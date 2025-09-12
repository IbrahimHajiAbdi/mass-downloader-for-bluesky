import json
import sqlite3
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from atproto_client.namespaces.sync_ns import ComAtprotoRepoNamespace
from atproto_client.models.com.atproto.repo.list_records import ParamsDict
from atproto import Client
from atproto.exceptions import AtProtocolError

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from mdfb.utils.constants import DELAY, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, RETRIES, DEFAULT_THREADS
from mdfb.utils.database import check_post_exists, connect_db
from mdfb.utils.helpers import split_list
from mdfb.utils.database import restore_posts
from mdfb.core.fetch_post_details import fetch_post_details

def _get_post_identifiers_base(
        client: Client, 
        did: str, 
        feed_type: str, 
        logger: logging.Logger, 
        cursor: str, 
        db_cursor: sqlite3.Cursor,
        limit: int = 0, 
        archive: bool = False, 
        update: bool = False
    ) -> dict:
    post_uris = []
    fetch_amount = 100 if archive else min(100, limit)
    res = _get_post_identifiers_with_retires(ParamsDict(
        collection=f"app.bsky.feed.{feed_type}",
        repo=did,
        limit=fetch_amount,
        cursor=cursor,
    ), client, fetch_amount, logger)  
    
    limit -= fetch_amount
    logger.info("Successful retrieved: %d posts, %d remaining", fetch_amount, limit)
    records = res.get("records", {})
    if not records:
        logger.info(f"No more records to fetch for DID: {did}, feed_type: {feed_type}")
        return {}
    last_record_cid = re.search(r"\w+$", records[-1]["uri"])[0]
    cursor = last_record_cid
    for record in records:
        if feed_type == "post":
            uri = record["uri"]
        else:
            uri = record["value"]["subject"]["uri"]
        if check_post_exists(db_cursor, did, record["uri"], feed_type) and update:
            res = {
                "cursor": cursor,
                "limit": limit,
                "post_uris": post_uris        
            }
            return {} if not post_uris else res
        uris = {
            "user_did": did,
            "user_post_uri": [record["uri"]],
            "feed_type": [feed_type],
            "poster_post_uri": uri,
        }
        post_uris.append(uris)
    res = {
        "cursor": cursor,
        "limit": limit,
        "post_uris": post_uris        
    }
    time.sleep(DELAY)
    return res

def get_post_identifiers(did: str, feed_type: str, limit: int = 0, archive: bool = False, update: bool = False, media_types: list[str] = None, num_threads: int = DEFAULT_THREADS, restore: bool = False) -> list[dict]:
    """
    get_post_identifiers: Gets the given amount AT-URIs of the posts wanted from the desired account 

    Args:
        did (str): DID of the target account
        feed_type (str): The type of post wanted from the account: like, repost and post
        limit (optional, default=0, int): The amount wanted to get
        archive (optional, default=False, bool): Will download all posts of the wanted type
        update (optional, default=True, bool): Will only latest posts that have not been downloaded
    Raises:
        SystemExit: If there is a failure to retreive posts

    Returns:
        list[dict]: A list of dictionaries of the desired AT-URIs from the post and user, user did and feed type 
    """
    if media_types:
        return _get_post_identifiers_media_types(did, feed_type, media_types, limit, archive, update, num_threads, restore)
    cursor = ""
    con = connect_db()
    db_cursor = con.cursor()
    post_uris = []
    logger = logging.getLogger(__name__)
    client = Client()

    while limit > 0 or archive:
        res = _get_post_identifiers_base(client, did, feed_type, logger, cursor, db_cursor, limit, archive, update)
        if res == {}:
            return post_uris
        post_uris.extend(res["post_uris"])
        limit = res["limit"]
        cursor = res["cursor"]
    return post_uris

def _get_post_identifiers_media_types(did: str, feed_type: str, media_types: list[str], limit: int = 0, archive: bool = False, update: bool = False, num_threads: int = DEFAULT_THREADS, restore: bool = False) -> list[dict]:
    cursor = ""
    con = connect_db()
    db_cursor = con.cursor()
    logger = logging.getLogger(__name__)
    client = Client()
    cursor = ""
    res = []

    while limit > 0 or archive or restore:
        if not restore:
            identifiers = _get_post_identifiers_base(client, did, feed_type, logger, cursor, db_cursor, limit, archive, update)   
            if identifiers == {}:
                return res
        post_details = []
        post_uris = identifiers.get("post_uris", []) if not restore else restore_posts(did, {feed_type: True})
        post_batchs = split_list(post_uris, num_threads)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for post_batch in post_batchs:
                futures.append(executor.submit(fetch_post_details, post_batch))
            for future in as_completed(futures):
                post_details.extend(future.result())

        for post in post_details:
            if "media_type" in post:
                for media_type in media_types:
                    if media_type in post["media_type"]:
                        res.append(post)
        if restore:
            break
        else:
            limit = identifiers["limit"]        
            cursor = identifiers["cursor"] 
    return res

def _get_post_identifiers_with_retires(params: ParamsDict, client: Client, fetch_amount: int, logger: logging.Logger):
    try:
        return _get_post_identifiers(params, client, fetch_amount, logger)
    except (AtProtocolError, RetryError) as e:
        logger.error(f"Failure to fetch posts: {e}", exc_info=True) 
        raise

@retry(
    wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX), 
    stop=stop_after_attempt(RETRIES)
)
def _get_post_identifiers(params: ParamsDict, client: Client, fetch_amount: int, logger: logging.Logger):
    try:
        logger.info(f"Attempting to fetch up to {fetch_amount} posts for DID: {params.get('repo')}, feed_type: {params.get('collection')}")
        res = ComAtprotoRepoNamespace(client).list_records(params)  
        res = json.loads(res.model_dump_json())
        return res
    except (AtProtocolError, RetryError):
        logger.error(f"Error occurred fetching posts from: {params}, fetch amount: {fetch_amount}", exc_info=True)
        raise