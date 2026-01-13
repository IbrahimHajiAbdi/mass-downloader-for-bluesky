import re
import time
import json
import logging

from atproto_client.namespaces.sync_ns import AppBskyFeedNamespace
from atproto_client.models.com.atproto.repo.list_records import ParamsDict
from atproto import Client
from atproto.exceptions import AtProtocolError

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from mdfb.utils.helpers import get_chunk
from mdfb.utils.constants import DELAY, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, RETRIES

class FetchPostDetails:

    BATCH_SIZE = 25

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.client = Client("https://public.api.bsky.app/")
        self.seen_uris = set()

    def fetch_post_details(self, uris: list[dict[str, str]]) -> list[dict[str, str]]:
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
            records = json.loads(res.model_dump_json())

            merged = self._merge_uri_chunk_to_records(uri_chunk, records)

            for post in merged:
                post_details = FetchPostDetails._process_post(post, self.seen_uris, self.logger)
                all_post_details.append(post_details)

            for uri in uri_chunk:
                if uri["poster_post_uri"] not in self.seen_uris:
                    self.logger.info(f"The post associated with this URI is missing/deleted: {uri.get('poster_post_uri')}")
            time.sleep(DELAY)
        return all_post_details

    @staticmethod
    def _process_post(post: dict, seen_uris: set, logger: logging.Logger) -> dict:
        uri = post["uri"]

        seen_uris.add(uri)
        post_details = FetchPostDetails._extract_post_details(post)
    
        embed_media = post["record"].get("embed", None)
        if not embed_media:
            return post_details

        embed_media = embed_media.get("media", embed_media)
        post_details.update(FetchPostDetails._extract_media(embed_media))
        
        logger.info("Post details retrieved for URI: %s", uri)
        return post_details

    @staticmethod
    def _extract_media(embed: dict) -> dict:
        """
        _extract_media: Extracts information from the media, or embed, key in the post details JSON response from the atproto API: app.bsky.feed.getPosts

        Args:
            embed (dict): The embed key from the API response of atproto API: app.bsky.feed.getPosts

        Returns:
            dict: The associated information from embed
        """
        media_links = {"media_type": []}
        if images := embed.get("images"):
            media_links["images_cid"] = [
                image["image"]["ref"]["link"] for image in images
            ]
            media_links["media_type"].extend(["image" * len(images)])
            media_links["mime_type"] = images[0]["image"]["mime_type"]

        if videos := embed.get("video"):
            media_links["media_type"].append("video")
            media_links["video_cid"] = videos["ref"]["link"]
            media_links["mime_type"] = videos["mime_type"]
               
        if not media_links["media_type"]:
            media_links["media_type"].append("text")

        return media_links

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
    
    @staticmethod
    def _get_rkey(at_uri: str) -> str:
        match = re.search(r"\w+$", at_uri)
        return match.group()

    @staticmethod
    def _get_author_details(author: dict) -> dict:
        author_details = {}
        author_details["did"] = author["did"]
        author_details["handle"] = author["handle"]
        author_details["display_name"] = author["display_name"]
        return author_details

    def _merge_uri_chunk_to_records(self, uri_chunk: list[dict], records: dict) -> list[dict]:
        merged = []

        for uris in uri_chunk:
            uri = uris["poster_post_uri"]
            for post in records["posts"]:
                if uri in post["uri"]:
                    combined = {**uris, **post}
                    merged.append(combined)
        return merged

    @staticmethod
    def _extract_post_details(post: dict) -> dict:
        post_details = {
            "rkey": FetchPostDetails._get_rkey(post["uri"]),
            "text": post["record"].get("text", ""),
            "response": post,
            **FetchPostDetails._get_author_details(post["author"])
        }

        # Optional only because the FetchFeedDetails class cannot get these values, and they are used in the database as 
        # the columns. Thus, you cannot add any of the post retrieved from feed to the database        
        optional_fields = ["user_did", "user_post_uri", "poster_post_uri", "feed_type"]
        for field in optional_fields:
            if field in post and post[field] is not None:
                post_details[field] = post[field]
        
        return post_details