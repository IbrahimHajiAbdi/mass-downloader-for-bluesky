import logging

from atproto import Client

from mdfb.core.media_types_fetcher import MediaTypesFetcher
from mdfb.core.uri_fetcher import URIFetcher
from mdfb.utils.constants import DEFAULT_THREADS
from mdfb.utils.database import Database


class PostIdentifierFetcher:
    def __init__(
        self,
        did: str,
        feed_type: str,
        db: Database,
        logger: logging.Logger | None = None,
        num_threads: int = DEFAULT_THREADS,
        restore: bool = False,
    ):
        self.did = did
        self.num_threads = num_threads
        self.feed_type = feed_type
        self.restore = restore
        self.client = Client()
        self.logger = logger or logging.getLogger(__name__)
        self.uri_fetcher = URIFetcher(self.did, self.feed_type, db, logger, num_threads)
        self.db = db

    def fetch(
        self, limit: int = 0, archive: bool = False, update: bool = False, media_types: list[str] | None = None
    ) -> list[dict]:
        if media_types:
            media_types_fetcher = MediaTypesFetcher(
                self.did, self.feed_type, self.db, media_types, self.logger, self.num_threads
            )
            return media_types_fetcher.fetch(media_types, limit, archive, update)
        return self._fetch_standard(limit, archive, update)

    def _fetch_standard(self, limit: int, archive: bool, update: bool) -> list[dict]:
        cursor = ""
        post_uris = []

        while limit > 0 or archive:
            res = self.uri_fetcher._fetch_batch(cursor, archive, limit, update)

            if not res:
                break

            post_uris.extend(res.post_uris)
            limit = res.limit
            cursor = res.cursor
        return post_uris
