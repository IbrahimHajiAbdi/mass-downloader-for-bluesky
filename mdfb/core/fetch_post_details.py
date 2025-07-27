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

def fetch_post_details(uris: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    fetch_post_details: Fetches post details from the given AT-URIs

    Args:
        uris (list[dict]): A list of dictionaries of the desired AT-URIs from the post and user, user did and feed type 

    Returns:
        list[dict]: A list of dictionaries that contain post details
    """
    all_post_details = []
    logger = logging.getLogger(__name__)
    seen_uris = set()
    client = Client("https://public.api.bsky.app/")
    
    for uri_chunk in get_chunk(uris, 25):
        logger.info(f"Fetching details from {len(uri_chunk)} URIs")
        res = _get_post_details_with_retries(uri_chunk, client, logger)
        if not res:
            continue
        records = json.loads(res.model_dump_json())

        merged = _merge_uri_chunk_to_records(uri_chunk, records)

        for post in merged:
            seen_uris.add(post["uri"])
            post_details = {
                "rkey": _get_rkey(post["uri"]),
                "text": post["record"].get("text", ""),
                "response": post,
                "user_did": post["user_did"],
                "user_post_uri": post["user_post_uri"],
                "poster_post_uri": post["poster_post_uri"],
                "feed_type": post["feed_type"],
                **_get_author_details(post["author"])
            }
        
            embed_media = post["record"].get("embed", None)
            if not embed_media:
                all_post_details.append(post_details)
                continue

            embed_media = embed_media.get("media", embed_media)
            post_details.update(_extract_media(embed_media))
            
            logger.info("Post details retrieved for URI: %s", post["uri"])
            all_post_details.append(post_details)
        for uris in uri_chunk:
            if uris["poster_post_uri"] not in seen_uris:

                logger.info(f"The post associated with this URI is missing/deleted: {uris.get('poster_post_uri')}")
        time.sleep(DELAY)
    return all_post_details

def _extract_media(embed: dict) -> dict:
    """
    _extract_media: Extracts information from the media, or embed, key in the post details JSON response from the atproto API: app.bsky.feed.getPosts

    Args:
        embed (dict): The embed key from the API response of atproto API: app.bsky.feed.getPosts

    Returns:
        dict: The associated information from embed
    """
    media_links = {}
    if embed.get("images"):
        for image_obj in embed["images"]:
            if "media_type" not in media_links:
                media_links["media_type"] = ["image"]
            else: 
                media_links["media_type"].append("image")
            image = image_obj["image"]["ref"]["link"]
            if "images_cid" not in media_links:
                media_links["images_cid"] = [image]
            else: 
                media_links["images_cid"].append(image)
            media_links["mime_type"] = image_obj["image"]["mime_type"]
    if embed.get("video"):
        if "media_type" not in media_links:
            media_links["media_type"] = ["video"]
        else: 
            media_links["media_type"].append("video")
        media_links["video_cid"] = embed["video"]["ref"]["link"]
        media_links["mime_type"] = embed["video"]["mime_type"]   
    if not embed.get("images") and not embed.get("video"):
        if "media_type" not in media_links:
            media_links["media_type"] = ["text"]
        else: 
            media_links["media_type"].append("text")
    return media_links

def _get_post_details_with_retries(uri_chunk: list[dict], client: Client, logger: logging.Logger):
    try:
        return _get_post_details(uri_chunk, client, logger)
    except (RetryError, AtProtocolError):
        logger.error(f"Failure to fetch records from the URIs: {uri_chunk}", exc_info=True)

@retry(
    wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX), 
    stop=stop_after_attempt(RETRIES)
)
def _get_post_details(uri_chunk: list[dict], client: Client, logger: logging.Logger):
    try:
        uris = [uris["poster_post_uri"] for uris in uri_chunk]
        res = AppBskyFeedNamespace(client).get_posts(ParamsDict(
            uris=uris
        ))
        return res
    except (AtProtocolError, RetryError):
        logger.error(f"Error occurred fetching records from URIs: {uri_chunk}", exc_info=True)
        raise
    
def _get_rkey(at_uri: str) -> str:
    match = re.search(r"\w+$", at_uri)
    return match.group()

def _get_author_details(author: dict) -> dict:
    author_details = {}
    author_details["did"] = author["did"]
    author_details["handle"] = author["handle"]
    author_details["display_name"] = author["display_name"]
    return author_details

def _merge_uri_chunk_to_records(uri_chunk: list[dict], records: dict) -> list[dict]:
    merged = []

    for uris in uri_chunk:
        uri = uris["poster_post_uri"]
        for post in records["posts"]:
            if uri in post["uri"]:
                combined = {**uris, **post}
                merged.append(combined)
    return merged