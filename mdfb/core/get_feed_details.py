import asyncio
import logging
import re

from atproto import AsyncClient

from mdfb.core.models import EnrichedPost
from mdfb.core.post_parser import PostParser
from mdfb.core.resolve_handle import resolve_handle
from mdfb.utils.config_manager import ConfigManager
from mdfb.utils.constants import DELAY


class FetchFeedDetails:
    BATCH_SIZE = 100
    FEED_URI_TEMPLATE = "at://{DID}/app.bsky.feed.generator/{FEED_NAME}"

    def __init__(self, handle: str, feed_url: str):
        self.logger = logging.getLogger(__name__)
        self.handle = handle
        self.config_manager = ConfigManager(handle)
        self.seen_uris = set()
        self.config_manager.existance_check()
        self._client: AsyncClient | None = None
        self.feed_url = feed_url
        self._validate_feed_url()

    async def _get_client(self) -> AsyncClient:
        if self._client is None:
            self._client = await ConfigManager(self.handle).get_authed_async_client()
        return self._client

    async def fetch(self, limit: int, media_types: list[str] | None = None) -> list[EnrichedPost]:
        feed_uri = self._resolve_feed()
        self.logger.info(f"Sucessfully resolved feed URL: {self.feed_url} to {feed_uri}")

        cursor = ""
        res = []

        while limit > 0:
            fetch_amount = min(limit, self.BATCH_SIZE)

            client = await self._get_client()
            data = await client.app.bsky.feed.get_feed({"feed": feed_uri, "limit": fetch_amount, "cursor": cursor})

            self.logger.info(f"Successfully retrieved {fetch_amount} posts from feed: {self.feed_url}, URI: {feed_uri}")

            posts = data

            processed_posts = PostParser.parse_and_filter(
                [p.post for p in posts.feed], self.seen_uris, self.logger, media_types
            )

            cursor = data.cursor
            limit -= len(
                processed_posts
            )  # Should have the same amount as fetch_amount if media_types != True else return valid posts retrieved

            res.extend(processed_posts)

            await asyncio.sleep(DELAY)
        return res

    def _resolve_feed(self) -> str:
        handle = PostParser.extract_handle(self.feed_url)
        did = resolve_handle(handle)
        feed_name = PostParser.extract_feed_name(self.feed_url)

        return self.FEED_URI_TEMPLATE.format_map({"DID": did, "FEED_NAME": feed_name})

    def _validate_feed_url(self):
        """
        Validates that the URL matches the Bluesky feed format:
        https://bsky.app/profile/{handle}/feed/{feed_name}
        """
        pattern = r"^https://bsky\.app/profile/[^/]+/feed/[^/]+$"

        if not re.match(pattern, self.feed_url):
            raise ValueError("Invalid feed URL format. Expected: https://bsky.app/profile/<handle>/feed/<feed_name>")
        self.logger.info(f"Valid feed URL given: {self.feed_url}")
