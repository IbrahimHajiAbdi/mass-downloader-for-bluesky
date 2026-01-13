import json
import re
import time
import logging
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from atproto_client.namespaces.sync_ns import ComAtprotoRepoNamespace
from atproto_client.models.com.atproto.repo.list_records import ParamsDict
from atproto import Client
from atproto.exceptions import AtProtocolError

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from mdfb.utils.constants import DELAY, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, RETRIES, DEFAULT_THREADS
from mdfb.utils.helpers import split_list
from mdfb.utils.database import Database
from mdfb.core.fetch_post_details import FetchPostDetails

@dataclass
class PostIdentifier:
    """Represents a post identifier with associated metadata."""
    user_did: str
    user_post_uri: list[str]
    feed_type: list[str]
    poster_post_uri: str


@dataclass
class FetchResult:
    """Result from fetching a batch of post identifiers."""
    cursor: str
    limit: int
    post_uris: list[dict]

class PostIdentifierFetcher:

    BATCH_SIZE = 100

    def __init__(self, did: str, feed_type: str, db: Database, logger: logging.Logger = None, num_threads: Optional[int] = DEFAULT_THREADS, restore: bool = False):
        self.did = did
        self.num_threads = num_threads
        self.feed_type = feed_type
        self.restore = restore
        self.client = Client()
        self.logger = logger if logger else logging.getLogger(__name__)
        self.db = db

    def fetch(self, limit: int = 0, archive: bool = False, update: bool = False, media_types: list[str] = None) -> list[dict]:
        if media_types:
            return self._fetch_with_media_filter(
                media_types, limit, archive, update
            )
        return self._fetch_standard(limit, archive, update)     

    def _fetch_standard(self, limit: int, archive: bool, update: bool) -> list[dict]:
        cursor = ""
        post_uris = []

        while limit > 0 or archive:
            res = self._fetch_batch(cursor, archive, limit, update)
            
            if not res:
                break

            post_uris.extend(res.post_uris)
            limit = res.limit
            cursor = res.cursor
        return post_uris    
    
    def _fetch_batch(self, cursor: str, archive: bool, limit: int, update: bool) -> Optional[FetchResult]:
        post_uris = []
        fetch_amount = self.BATCH_SIZE if archive else min(self.BATCH_SIZE, limit)

        res = self._fetch_with_retry(ParamsDict(
            collection=f"app.bsky.feed.{self.feed_type}",
            repo=self.did,
            limit=fetch_amount,
            cursor=cursor,
        ), fetch_amount)

        remaining_amount = limit - fetch_amount
        self.logger.info("Successfully retrieved: %d posts, %d remaining", fetch_amount, limit)
        records = res.get("records", {})
        
        if not records:
            self.logger.info(f"No more records to fetch for DID: {self.did}, feed_type: {self.feed_type}")
            return None
        
        cursor = self._extract_cursor(records[-1]["uri"])

        for record in records:
            if update and self.db.check_post_exists(self.did, record["uri"], self.feed_type):
                if post_uris:
                    return FetchResult(
                        cursor=cursor,
                        limit=remaining_amount,
                        post_uris=post_uris
                    )
                return None
        
            post_uris.append(self._create_post_identifier(record))
        
        time.sleep(DELAY)

        return FetchResult(
            cursor=cursor,
            limit=remaining_amount,
            post_uris=post_uris
        )

    def _fetch_with_media_filter(self, media_types: list[str], limit: int = 0, archive: bool = False, update: bool = False) -> list[dict]:
        cursor = ""
        res = []

        while limit > 0 or archive or self.restore:
            if self.restore:
                post_uris = self.db.restore_posts(self.did, {self.feed_type: True})
                self.logger.info(f"Successfully restored post identifiers from database for did: {self.did} and feed_type: {self.feed_type}")
            else:
                identifiers = self._fetch_batch(cursor, archive, limit, update)
                if not identifiers:
                    break
                post_uris = identifiers.post_uris

            post_details = self._fetch_details_parallel(post_uris, media_types)

            res.extend(PostIdentifierFetcher._filter_media_types(post_details, media_types))

            if self.restore:
                break

            limit = identifiers.limit
            cursor = identifiers.cursor

        return res

    def _fetch_details_parallel(self, post_uris: list[dict], media_types: list[str]) -> list[dict]:
        post_details = []
        post_batchs = split_list(post_uris, self.num_threads)
        fetchPost = FetchPostDetails()

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = []
            for post_batch in post_batchs:
                futures.append(executor.submit(fetchPost.fetch_post_details, post_batch))
            for future in as_completed(futures):
                post_details.extend(future.result())

        return post_details

    @staticmethod    
    def _filter_media_types(post_details: list[dict], media_types: list[str]) -> list[dict]:
        filtered_posts = []
        for post in post_details:
                if "media_type" in post:
                    for media_type in media_types:
                        if media_type in post["media_type"]:
                            filtered_posts.append(post)
        return filtered_posts
   
    def _extract_cursor(self, uri: str) -> str:
        match = re.search(r"\w+$", uri)
        return match[0] if match else ""

    def _create_post_identifier(self, record: dict) -> dict:
        if self.feed_type == "post":
            uri = record["uri"]
        else:
            uri = record["value"]["subject"]["uri"]

        uris = {
            "user_did": self.did,
            "user_post_uri": [record["uri"]],
            "feed_type": [self.feed_type],
            "poster_post_uri": uri,
        }
        return uris
        
    def _fetch_with_retry(self, params: ParamsDict, fetch_amount: int) -> dict:
        try:
            return self._fetch_from_api(params, fetch_amount)
        except (AtProtocolError, RetryError) as e:
            self.logger.error(f"Failed to fetch posts: {e}", exc_info=True)
            raise
    
    @retry(
        wait=wait_exponential(
            multiplier=EXP_WAIT_MULTIPLIER, 
            min=EXP_WAIT_MIN, 
            max=EXP_WAIT_MAX
        ),
        stop=stop_after_attempt(RETRIES)
    )
    def _fetch_from_api(self, params: ParamsDict, fetch_amount: int) -> dict:
        try:
            self.logger.info(
                f"Attempting to fetch up to {fetch_amount} posts for "
                f"DID: {params.get('repo')}, feed_type: {params.get('collection')}"
            )
            
            response = ComAtprotoRepoNamespace(self.client).list_records(params)
            return json.loads(response.model_dump_json())
            
        except (AtProtocolError, RetryError):
            self.logger.error(
                f"Error occurred fetching posts from: {params}, "
                f"fetch amount: {fetch_amount}",
                exc_info=True
            )
            raise