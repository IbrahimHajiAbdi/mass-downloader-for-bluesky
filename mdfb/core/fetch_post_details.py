import time
import logging

from atproto_client.namespaces.sync_ns import AppBskyFeedNamespace
from atproto_client.models.app.bsky.feed.get_posts import ParamsDict
from atproto import Client
from atproto.exceptions import AtProtocolError
from atproto_client.models.app.bsky.feed.defs import PostView

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from mdfb.utils.helpers import get_chunk
from mdfb.utils.constants import DELAY, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, RETRIES
from mdfb.core.post_parser import PostParser
from mdfb.core.models import EnrichedPost

class FetchPostDetails:

    BATCH_SIZE = 25

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        self.client = Client("https://public.api.bsky.app/")
        self.seen_uris = set()

    def fetch_post_details(self, uris: list[dict[str, str]]) -> list[EnrichedPost]:
        """
        fetch_post_details: Fetches post details from the given AT-URIs

        Args:
            uris (list[dict]): A list of dictionaries of the desired AT-URIs from the post and user, user did and feed type 

        Returns:
            list[dict]: A list of dictionaries that contain post details
        """
        all_post_details = []
        
        for uri_chunk in get_chunk(uris, self.BATCH_SIZE):
            self.logger.info(f"Fetching details from {len(uri_chunk)} URIs")
            res = self._get_post_details_with_retries(uri_chunk)
            if not res:
                continue
            records = res.posts

            # Convert default PostView into EnrichedPost for later enrichment
            # records = [EnrichedPost(response=record) for record in records]

            merged = self._merge_uri_chunk_to_records(uri_chunk, records)

            for post, enriched_data in merged:
                post_details = PostParser.parse_post(post, self.seen_uris, self.logger)
                # Enrich the post with data from the uri chucks
                for k, v in enriched_data.items():
                    setattr(post_details, k, v)
                all_post_details.append(post_details)

            for uri in uri_chunk:
                if uri["poster_post_uri"] not in self.seen_uris:
                    self.logger.info(f"The post associated with this URI is missing/deleted: {uri.get('poster_post_uri')}")
            time.sleep(DELAY)
        return all_post_details

    def _get_post_details_with_retries(self, uri_chunk: list[dict]):
        try:
            return self._get_post_details(uri_chunk)
        except (RetryError, AtProtocolError):
            self.logger.error(f"Failure to fetch records from the URIs: {uri_chunk}", exc_info=True)

    @retry(
        wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX), 
        stop=stop_after_attempt(RETRIES)
    )
    def _get_post_details(self, uri_chunk: list[dict]):
        try:
            uris = [uris["poster_post_uri"] for uris in uri_chunk]
            res = AppBskyFeedNamespace(self.client).get_posts(ParamsDict(
                uris=uris
            ))
            return res
        except (AtProtocolError, RetryError):
            self.logger.error(f"Error occurred fetching records from URIs: {uri_chunk}", exc_info=True)
            raise
    
    def _merge_uri_chunk_to_records(self, uri_chunk: list[dict], records: list[PostView]) -> list[tuple[PostView, dict]]:
        merged = []

        for uris in uri_chunk:
            uri = uris["poster_post_uri"]
            for post in records:
                if uri == post.uri:
                    # for k, v in uris.items():
                    #     setattr(post, k, v)
                    merged.append((post, uris))
        return merged