import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from atproto import Client

from mdfb.core.fetch_post_details import FetchPostDetails
from mdfb.core.models import EnrichedPost
from mdfb.core.post_parser import PostParser
from mdfb.core.uri_fetcher import URIFetcher
from mdfb.utils.constants import DEFAULT_THREADS
from mdfb.utils.database import Database
from mdfb.utils.helpers import split_list


class MediaTypesFetcher:
    def __init__(
        self,
        did: str,
        feed_type: str,
        db: Database,
        media_types: list[str],
        logger: logging.Logger | None = None,
        num_threads: int = DEFAULT_THREADS,
        restore: bool = False,
    ):
        self.did = did
        self.num_threads = num_threads
        self.feed_type = feed_type
        self.restore = restore
        self.media_types = media_types
        self.client = Client()
        self.logger = logger or logging.getLogger(__name__)
        self.uri_fetcher = URIFetcher(self.did, self.feed_type, db, logger, num_threads)
        self.db = db

    def fetch(self, media_types: list[str], limit: int = 0, archive: bool = False, update: bool = False) -> list[dict]:
        cursor = ""
        res = []

        while limit > 0 or archive or self.restore:
            if self.restore:
                post_uris = self.db.restore_posts(self.did, {self.feed_type: True})
                self.logger.info(
                    f"Successfully restored post identifiers from database for did: {self.did} and feed_type: {self.feed_type}"
                )
            else:
                identifiers = self.uri_fetcher._fetch_batch(cursor, archive, limit, update)
                if not identifiers:
                    break
                post_uris = identifiers.post_uris

            post_details = self._fetch_details_parallel(post_uris)

            res.extend(PostParser._filter_media_types(post_details, media_types))

            if self.restore:
                break

            limit = identifiers.limit
            cursor = identifiers.cursor

        return res

    def _fetch_details_parallel(self, post_uris: list[dict]) -> list[EnrichedPost]:
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
