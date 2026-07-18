import logging
import time

from atproto.exceptions import AtProtocolError
from atproto_client.models.app.bsky.bookmark.get_bookmarks import ParamsDict, Response
from atproto_client.models.app.bsky.feed.defs import BlockedPost, NotFoundPost, PostView
from atproto_client.namespaces.sync_ns import AppBskyBookmarkNamespace
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from mdfb.core import resolve_handle
from mdfb.core.models import EnrichedPost
from mdfb.core.post_parser import PostParser
from mdfb.utils.config_manager import ConfigManager
from mdfb.utils.constants import DELAY, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, RETRIES, FeedTypes
from mdfb.utils.database import Database


class BookmarkFetcher:
    BATCH_SIZE = 50

    def __init__(self, handle: str, db: Database, logger: logging.Logger | None = None, did: str = ""):
        self.handle = handle
        self.did = did or resolve_handle.resolve_handle(handle)
        self.config_manager = ConfigManager(handle)
        self.client = ConfigManager(handle).get_authed_client()
        self.logger = logger or logging.getLogger(__name__)
        self.db = db
        self.feed_type = FeedTypes.BOOKMARK
        self.seen_uris = set()

    def fetch_bookmarks(
        self, limit: int = 0, archive: bool = False, update: bool = False, media_types: list[str] | None = None
    ) -> list[EnrichedPost]:
        """
        fetch_bookmarks: Fetches post details from bookmarks

        Args:
            limit (int, optional): Number of posts to download, in batches of
                `BATCH_SIZE`. Ignored if `archive` or `update` is True — in
                either of those cases, fetching continues regardless of
                `limit`. Defaults to 0, in which case no posts are fetched
                unless `archive` or `update` is True.
            archive (bool, optional): If True, fetches all bookmarks,
                continuing until no more bookmarks are returned by the API.
                Defaults to False.
            update (bool, optional): If True, fetches bookmarks until either
                no more bookmarks are returned by the API, or a post already
                present in the database (for the current DID and feed_type)
                is encountered, whichever comes first. Defaults to False.
            media_types (list[str] | None, optional): List of media types to
                filter bookmarked posts by (e.g. images, video). Currently
                unused — accepted but not applied anywhere in the fetch or
                parse pipeline. Defaults to None.

        Returns:
            list[EnrichedPost]: A list of enriched posts

        """
        all_post_details = []

        bookmarks = self._get_bookmarks(limit, archive, update)

        for post in bookmarks:
            post_details = PostParser.parse_post(post, self.seen_uris, self.logger)
            for k, v in self._create_post_identifier(post).items():
                setattr(post_details, k, v)
            all_post_details.append(post_details)

        if media_types:
            return PostParser.filter_media_types(all_post_details, media_types)
        return all_post_details

    def _get_bookmarks(self, limit: int = 0, archive: bool = False, update: bool = False) -> list[PostView]:
        cursor = ""
        bookmarks = []
        while limit > 0 or archive or update:
            res_raw = self._fetch_from_api(ParamsDict(cursor=cursor), self.BATCH_SIZE)

            time.sleep(DELAY)
            cursor = res_raw.cursor
            res = self._validate_bookmarks(res_raw)
            limit -= self.BATCH_SIZE

            for post in res:
                if update and self.db.check_post_exists(self.did, post.uri, self.feed_type):
                    return bookmarks
                bookmarks.append(post)

            if not cursor:
                break
        return bookmarks

    @retry(
        wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX),
        stop=stop_after_attempt(RETRIES),
    )
    def _fetch_from_api(self, params: ParamsDict, fetch_amount: int) -> Response:
        try:
            self.logger.info(f"Attempting to fetch up to {fetch_amount} bookmarks for DID: {self.did}")

            return AppBskyBookmarkNamespace(self.client).get_bookmarks(params)

        except (AtProtocolError, RetryError):
            self.logger.exception(f"Error occurred fetching posts from: {params}, fetch amount: {fetch_amount}")
            raise

    def _validate_bookmarks(self, bookmarks: Response) -> list[PostView]:
        res: list[PostView] = []

        for bookmark_view in bookmarks.bookmarks:
            bookmark = bookmark_view.item
            if isinstance(bookmark, BlockedPost):
                self.logger.warning(f"The post for URI {bookmark.uri} is blocked.")
            elif isinstance(bookmark, NotFoundPost):
                self.logger.warning(f"The post for URI {bookmark.uri} cannot be found on the bsky network.")
            else:
                res.append(bookmark)
        return res

    def _create_post_identifier(self, post: PostView) -> dict[str, str | list]:
        return {
            "user_did": self.did,
            "user_post_uri": [post.uri],
            "feed_type": [self.feed_type],
            "poster_post_uri": post.uri,
        }
