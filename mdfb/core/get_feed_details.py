import logging
import platformdirs
import os
import yaml
import re
import json
import time

from atproto import Client

from mdfb.core.resolve_handle import resolve_handle
from mdfb.core.fetch_post_details import FetchPostDetails
from mdfb.core.get_post_identifiers import PostIdentifierFetcher
from mdfb.utils.constants import DELAY

class FetchFeedDetails():

    BATCH_SIZE = 100
    FEED_URI_TEMPLATE = "at://{DID}/app.bsky.feed.generator/{FEED_NAME}"

    def __init__(self, handle: str, feed_url: str):
        self.logger = logging.getLogger(__name__)
        self.handle = handle
        self.seen_uris = set()
        self._existance_check()
        self.client = Client()
        self._login()
        self.feed_url = feed_url
        self._validate_feed_url()
    
    def fetch(self, limit: int, media_types: list[str] = None) -> list[dict]:
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

            posts = json.loads(data.model_dump_json())

            processed_posts = self._process_batch_posts(posts)

            if media_types:
                processed_posts = PostIdentifierFetcher._filter_media_types(processed_posts, media_types)
                self.logger.info(f"Media types detected {media_types}, filtered posts from {fetch_amount} to {len(processed_posts)} valid posts")

            cursor = data.cursor
            limit -= len(processed_posts) # Should the same amount as fetch_amount if media_types != True else return valid posts retrieved

            res.extend(processed_posts)

            time.sleep(DELAY)
        return res

    def _process_batch_posts(self, posts: list[dict]) -> list[dict]:
        processed = []
        
        for post in posts["feed"]:
            processed_post = FetchPostDetails._process_post(post["post"], self.seen_uris, self.logger)
            processed.append(processed_post)
        self.logger.info(f"Successfully processed {len(processed)} posts")
        return processed


    def _resolve_feed(self) -> str:
        handle = self._extract_handle()
        did = resolve_handle(handle)
        feed_name = self._extract_feed_name()

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

    def _extract_handle(self) -> str:
        """Extracts just the handle."""
        pattern = r'https://bsky\.app/profile/([^/]+)/feed/[^/]+'
        match = re.search(pattern, self.feed_url)
        return match.group(1)

    def _extract_feed_name(self) -> str:
        """Extracts just the feed name."""
        pattern = r'https://bsky\.app/profile/[^/]+/feed/([^/]+)'
        match = re.search(pattern, self.feed_url)
        return match.group(1)

    def _existance_check(self):
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")

        if not os.path.isfile(file):
            msg = f"There is no config yaml at: {file}. Need to login using `mdfb login`"
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.info("Config yaml found")

    def _fetch_app_password(self) -> str:
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")
        config = yaml.safe_load(open(file))
        self.logger.info(f"Successfully loaded config yaml {file}")

        if self.handle not in config:
            msg = f"There is no entry for handle: {self.handle} in the config yaml, need to use `mdfb login` to add an entry."
            self.logger.error(msg)
            raise ValueError(msg)
        return config[self.handle]["app_password"]
    
    def _login(self):
        try:
            self.client.login(self.handle, self._fetch_app_password())
        except Exception:
            msg = "There is an error logging in. App password may be expired or deleted. Please log in again via `mdfb login`"
            self.logger.error(msg)
            raise ValueError(msg)
