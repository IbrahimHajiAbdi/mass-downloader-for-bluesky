import json
import os
import re
import time
import encodings
import logging

from atproto_client.namespaces.sync_ns import ComAtprotoSyncNamespace
from atproto_client.models.com.atproto.repo.list_records import ParamsDict
from atproto import Client

from pathvalidate import sanitize_filename
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional

from mdfb.utils.constants import DELAY, RETRIES, EXP_WAIT_MAX, EXP_WAIT_MIN, EXP_WAIT_MULTIPLIER, VALID_FILENAME_OPTIONS
from mdfb.utils.database import Database


class DownloadBlobs():
    def __init__(self, logger: logging.Logger, file_path: str, db: Database, filename_format_string: str, include: str = None):
        self.logger = logger or logging.getLogger(__name__)
        self.file_path = file_path
        self.db = db
        self.filename_format_string = filename_format_string or "{RKEY}_{HANDLE}_{TEXT}"
        self.include = include

    def download_blobs(self, posts: list[dict], progress_bar: tqdm) -> None:
        """
        download_blobs: for the given posts, returned from fetch_post_details(), and filepath, downloads the associated blobs for each post.

        Args:
            posts (list[dict]): post details returned from fetch_post_details()
            progress_bar (tqdm): progress bar
        """
        sucessful_downloads = []

        for post in posts:
            did = post["did"]
            filename_options = {}
            for valid_filename_option in VALID_FILENAME_OPTIONS:
                if valid_filename_option in self.filename_format_string:
                    filename_options[valid_filename_option] = post[valid_filename_option.lower()]
            filename = self._make_base_filename(filename_options)
            if self.include:
                if "json" in self.include:
                    self._download_json(filename, post)
                    time.sleep(DELAY)
                elif "media" in self.include:
                    self._download_media(post, filename, did)
            else:
                self._download_media(post, filename, did)
                self._download_json(filename, post)  
            
            rows = self._successful_download(post, progress_bar)
            if rows:
                sucessful_downloads.extend(rows)
        self.db.insert_post(sucessful_downloads)
        self.db.connection.commit()

    def _get_blob_with_retries(self, did: str, cid: str, filename: str):
        try:
            self._get_blob(did, cid, filename)
            return True
        except Exception:
            self.logger.error(f"Error occured for downloading this file, DID: {did}, CID: {cid}, after {RETRIES} retires", exc_info=True)
            return False

    @retry(
        wait=wait_exponential(multiplier=EXP_WAIT_MULTIPLIER, min=EXP_WAIT_MIN, max=EXP_WAIT_MAX), 
        stop=stop_after_attempt(RETRIES)
    )
    def _get_blob(self, did: str, cid: str, filename: str) -> bool:
        try:
            res = ComAtprotoSyncNamespace(Client()).get_blob(ParamsDict(
                    did=did,
                    cid=cid
            ))
            with open(os.path.join(self.file_path, filename), "wb") as file:
                file.write(res)
        except Exception:
            self.logger.error(f"Error occured for downloading this file, DID: {did}, CID: {cid}", exc_info=True)
            raise 
        
    def _make_base_filename(self, filename_options: dict) -> str:
        filename = self.filename_format_string.format(**filename_options)
        filename = self._truncate_filename(filename, 245)
        return sanitize_filename(filename)

    def _append_extension(self, base_filename: str, mime_type: str = None, i: int = None) -> str:
        filename = base_filename
        if i:
            filename += f"_{i}"
        if mime_type:
            file_type = re.search(r"\w+$", mime_type).group()
            filename += f".{file_type}"
        return filename

    def _download_media(self, post: dict, filename: str, did: str):
        if "video_cid" in post:
            video_filename = self._append_extension(filename, post["mime_type"])
            success = self._get_blob_with_retries(did, post["video_cid"], video_filename)
            if success:
                self.logger.info(f"Successful downloaded video: {video_filename}")
            time.sleep(DELAY)

        if "images_cid" in post:
            for index, image_cid in enumerate(post["images_cid"]):
                if len(post["images_cid"]) > 1:
                    image_filename = self._append_extension(filename, post["mime_type"], index + 1)
                else: image_filename = self._append_extension(filename, post["mime_type"])
                success = self._get_blob_with_retries(did, image_cid, image_filename)
                if success:
                    self.logger.info(f"Successful downloaded image: {image_filename}")
                time.sleep(DELAY)

    def _download_json(self, filename: str, post: dict):
        with open(f"{os.path.join(self.file_path, filename)}.json", "wt") as json_file:
            json.dump(post["response"], json_file, indent=4)
        self.logger.info(f"Successfully wrote file: {filename + '.json'}")

    def _truncate_filename(self, filename: str, MAX_BYTE: int) -> str:
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

    def _successful_download(self, post: dict, progress_bar: tqdm) -> Optional[list[tuple]]:
        res = []
        required_keys = ["feed_type", "user_post_uri", "user_did", "poster_post_uri"]
        if all(key in post for key in required_keys):
            for i in range(len(post["feed_type"])):
                res.append((
                    post["user_did"], 
                    post["user_post_uri"][i], 
                    post["feed_type"][i], 
                    post["poster_post_uri"]
                ))
        progress_bar.update(1)
        return res