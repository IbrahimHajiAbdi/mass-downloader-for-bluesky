import json
import os
from atproto_client.namespaces.sync_ns import ComAtprotoSyncNamespace
from atproto_client.models.com.atproto.repo.list_records import ParamsDict
from atproto import Client
import re, time
from pathvalidate import sanitize_filename
import encodings
import logging
from mdfb.utils.constants import DELAY, RETRIES, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, VALID_FILENAME_OPTIONS
from tqdm import tqdm

from tenacity import retry, stop_after_attempt, wait_exponential

def download_blobs(posts: list[dict], file_path: str, progress_bar: tqdm, filename_format_string: str = "{RKEY}_{HANDLE}_{TEXT}") -> None:
    """
    download_blobs: for the given posts, returned from fetch_post_details(), and filepath, downloads the associated blobs for each post.

    Args:
        posts (list[dict]): post details returned from fetch_post_details()
        file_path (str): filepath for where the files will be stored
        progress_bar (tqdm): progress bar
    """
    logger = logging.getLogger(__name__)
    for post in posts:
        did = post["did"]
        filename_options = {}
        for valid_filename_option in VALID_FILENAME_OPTIONS:
            if valid_filename_option in filename_format_string:
                filename_options[valid_filename_option] = post[valid_filename_option.lower()]
        filename = _make_base_filename(filename_options, filename_format_string)
        if "video_cid" in post:
            video_filename = _append_extension(filename, post["mime_type"])
            success = _get_blob_with_retries(did, post["video_cid"], video_filename, file_path, logger)
            if success:
                logger.info(f"Successful downloaded video: {video_filename}")
            time.sleep(DELAY)

        if "images_cid" in post:
            for index ,image_cid in enumerate(post["images_cid"]):
                if len(post["images_cid"]) > 1:
                    image_filename = _append_extension(filename, post["mime_type"], index + 1)
                else: image_filename = _append_extension(filename, post["mime_type"])
                success = _get_blob_with_retries(did, image_cid, image_filename, file_path, logger)
                if success:
                    logger.info(f"Successful downloaded image: {image_filename}")
                time.sleep(DELAY)
                
        with open(f"{os.path.join(file_path, filename)}.json", "wt") as json_file:
            json.dump(post["response"], json_file, indent=4)
        logger.info(f"Sucessful wrote file: {filename + ".json"}")
        progress_bar.update(1)

def _get_blob_with_retries(did: str, cid: str, filename: str, file_path: str, logger: logging.Logger):
    try:
        _get_blob(did, cid, filename, file_path, logger)
        return True
    except Exception:
        logger.error(f"Error occured for downloading this file, DID: {did}, CID: {cid}, after {RETRIES} retires", exc_info=True)
        return False

@retry(
    wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX), 
    stop=stop_after_attempt(RETRIES)
)
def _get_blob(did: str, cid: str, filename: str, file_path: str, logger: logging.Logger) -> bool:
    try:
        res = ComAtprotoSyncNamespace(Client()).get_blob(ParamsDict(
                did=did,
                cid=cid
        ))
        with open(os.path.join(file_path, filename), "wb") as file:
            file.write(res)
    except Exception:
        logger.error(f"Error occured for downloading this file, DID: {did}, CID: {cid}")
        raise 
    
def _make_base_filename(filename_options: dict, format_filename: str) -> str:
    filename = format_filename.format(**filename_options)
    filename = _truncate_filename(filename, 245)
    return sanitize_filename(filename)

def _append_extension(base_filename: str, mime_type: str = None, i: int = None) -> str:
    filename = base_filename
    if i:
        filename += f"_{i}"
    if mime_type:
            file_type = re.search(r"\w+$", mime_type).group()
            filename += f".{file_type}"
    return filename
    
def _truncate_filename(filename: str, MAX_BYTE: int) -> str:
    """
    _truncate_filename: truncates the given filename to the maximum number of bytes given, or less. This is only for utf-8 encoded strings and 
    if the filename at the maximum number of bytes is an invalid utf-8 string, then it removes one byte from the end so the string is valid.

    Args:
        filename (str): string of the filename
        MAX_BYTE (int): maximum bytes allowed

    Returns:
        str: truncated filename such that it is within the maximum number of bytes
    """
    byte_len = 0
    iter_encoder = encodings.search_function("utf-8").incrementalencoder()
    for i, char in enumerate(filename):
        byte_len += len(iter_encoder.encode(char))
        if byte_len > MAX_BYTE:
            return filename[:i]
    return filename