import logging
import os
import re
from mdfb.utils.constants import MAX_THREADS

def validate_directory(directory: str) -> str:
    if not os.path.exists(directory) or not os.path.isdir(directory):
        raise ValueError("The given filepath is either not valid or does not exist")
    return directory.rstrip("/")

def validate_limit(limit: str) -> int:
    if not limit.isdigit():
        raise ValueError("The given limit is not a integer")
    elif int(limit) < 1:
        raise ValueError("The given limit is 0 or less")
    return int(limit)

def validate_did(did: str) -> str:
    if not re.search(r"^did:[a-z]+:[a-zA-Z0-9._:%-]*[a-zA-Z0-9._-]$", did):
        raise ValueError("The given DID is not valid")
    return did

def validate_threads(threads: str) -> int:
    if not threads.isdigit():
        raise ValueError("Please enter an integer")
    threads = int(threads)
    if threads > MAX_THREADS:
        logging.info(f"Entered {threads} threads, but the maximum is {MAX_THREADS}. Setting to {MAX_THREADS} threads")
        print(f"Entered {threads} threads, but the maximum is {MAX_THREADS}. Setting to {MAX_THREADS} threads.")
        threads = MAX_THREADS
    if threads < 1:
        raise ValueError("Please set threads to 1 or more")
    return threads

def validate_no_posts(posts: list, account: str, post_types: list):
    if not posts:
        raise ValueError(f"There are no posts associated with account: {account}, for post_type(s): {post_types}")