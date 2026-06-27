import logging
import re
import time

from atproto import Client

from mdfb.core.config_manager import ConfigManager
from mdfb.core.models import EnrichedPost
from mdfb.core.post_parser import PostParser
from mdfb.core.resolve_handle import resolve_handle
from mdfb.core.get_post_identifiers import PostIdentifierFetcher

from atproto_client.models.app.bsky.feed.get_feed import Response
from mdfb.utils.constants import DELAY

class FetchFeedDetails():

    BATCH_SIZE = 100
    FEED_URI_TEMPLATE = "at://{DID}/app.bsky.feed.generator/{FEED_NAME}"

    def __init__(self, handle: str, feed_url: str):
        self.logger = logging.getLogger(__name__)
        self.handle = handle
        self.config_manager = ConfigManager(handle)
        self.seen_uris = set()
        self.config_manager._existance_check()
        self.client = Client()
        self._login()
        self.feed_url = feed_url
        self._validate_feed_url()
    
    def fetch(self, limit: int, media_types: list[str] | None = None) -> list[EnrichedPost]:
        feed_uri = self._resolve_feed()
        self.logger.info(f"Sucessfully resolved feed URL: {self.feed_url} to {feed_uri}")

        cursor = ""
        res = []

        while limit > 0:
            fetch_amount = self.BATCH_SIZE if limit > self.BATCH_SIZE else limit

            data = self.client.app.bsky.feed.get_feed({
                'feed': feed_uri,
                'limit': fetch_amount,
                'cursor': cursor
            })
            
            self.logger.info(f"Successfully retrieved {fetch_amount} posts from feed: {self.feed_url}, URI: {feed_uri}")

            posts = data

            processed_posts = self._process_batch_posts(posts)

            if media_types:
                processed_posts = PostIdentifierFetcher._filter_media_types(processed_posts, media_types)
                self.logger.info(f"Media types detected {media_types}, filtered posts from {fetch_amount} to {len(processed_posts)} valid posts")

            cursor = data.cursor
            limit -= len(processed_posts) # Should have the same amount as fetch_amount if media_types != True else return valid posts retrieved

            res.extend(processed_posts)

            time.sleep(DELAY)
        return res

    def _process_batch_posts(self, posts: Response) -> list[EnrichedPost]:
        processed = []
        
        for post in getattr(posts, "feed"):
            processed_post = PostParser.parse_post(getattr(post, "post"), self.seen_uris, self.logger)
            processed.append(processed_post)
        self.logger.info(f"Successfully processed {len(processed)} posts")
        return processed


    def _resolve_feed(self) -> str:
        handle = PostParser._extract_handle(self.feed_url)
        did = resolve_handle(handle)
        feed_name = PostParser._extract_feed_name(self.feed_url)

        return self.FEED_URI_TEMPLATE.format_map({
            'DID': did,
            'FEED_NAME': feed_name
        })

    def _validate_feed_url(self):
        """
        Validates that the URL matches the Bluesky feed format:
        https://bsky.app/profile/{handle}/feed/{feed_name}
        """
        pattern = r'^https://bsky\.app/profile/[^/]+/feed/[^/]+$'
        
        if not re.match(pattern, self.feed_url):
            raise ValueError(
                "Invalid feed URL format. Expected: https://bsky.app/profile/<handle>/feed/<feed_name>"
            )
        self.logger.info(f"Valid feed URL given: {self.feed_url}")
    
    def _login(self):
        try:
            self.client.login(self.handle, self.config_manager._fetch_app_password())
        except Exception:
            msg = "There is an error logging in. App password may be expired or deleted. Please log in again via `mdfb login`"
            self.logger.error(msg)
            raise ValueError(msg)
