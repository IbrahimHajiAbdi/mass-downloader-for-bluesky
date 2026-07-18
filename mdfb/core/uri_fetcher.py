import json
import logging
import time
from dataclasses import dataclass

from atproto import Client
from atproto.exceptions import AtProtocolError
from atproto_client.models.com.atproto.repo.list_records import ParamsDict
from atproto_client.namespaces.sync_ns import ComAtprotoRepoNamespace
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from mdfb.core.post_parser import PostParser
from mdfb.utils.constants import DEFAULT_THREADS, DELAY, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, RETRIES
from mdfb.utils.database import Database


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


class URIFetcher:
    BATCH_SIZE = 100

    def __init__(
        self,
        did: str,
        feed_type: str,
        db: Database,
        logger: logging.Logger | None = None,
        num_threads: int = DEFAULT_THREADS,
    ) -> None:
        self.feed_type = feed_type
        self.did = did
        self.num_threads = num_threads
        self.feed_type = feed_type
        self.client = Client()
        self.logger = logger or logging.getLogger(__name__)
        self.db = db

    def _fetch_batch(self, cursor: str, archive: bool, limit: int, update: bool) -> FetchResult | None:
        post_uris = []
        fetch_amount = self.BATCH_SIZE if archive else min(self.BATCH_SIZE, limit)

        res = self._fetch_with_retry(
            ParamsDict(
                collection=f"app.bsky.feed.{self.feed_type}",
                repo=self.did,
                limit=fetch_amount,
                cursor=cursor,
            ),
            fetch_amount,
        )

        remaining_amount = limit - fetch_amount
        self.logger.info("Successfully retrieved: %d posts, %d remaining", fetch_amount, limit)
        records = res.get("records", {})

        if not records:
            self.logger.info(f"No more records to fetch for DID: {self.did}, feed_type: {self.feed_type}")
            return None

        cursor = PostParser._extract_cursor(records[-1]["uri"])

        for record in records:
            if update and self.db.check_post_exists(self.did, record["uri"], self.feed_type):
                return (
                    FetchResult(cursor=cursor, limit=remaining_amount, post_uris=post_uris) if not post_uris else None
                )

            post_uris.append(PostParser._create_post_identifier(self.feed_type, self.did, record))

        time.sleep(DELAY)

        return FetchResult(cursor=cursor, limit=remaining_amount, post_uris=post_uris)

    def _fetch_with_retry(self, params: ParamsDict, fetch_amount: int) -> dict:
        try:
            return self._fetch_from_api(params, fetch_amount)
        except (AtProtocolError, RetryError) as e:
            self.logger.error(f"Failed to fetch posts: {e}", exc_info=True)
            raise

    @retry(
        wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX),
        stop=stop_after_attempt(RETRIES),
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
                f"Error occurred fetching posts from: {params}, fetch amount: {fetch_amount}", exc_info=True
            )
            raise
