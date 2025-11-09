import logging
import os
import re
import string
import argparse
from mdfb.utils.constants import MAX_THREADS, VALID_FILENAME_OPTIONS
from mdfb.utils.database import Database

def validate_directory(directory: str, parser: argparse.ArgumentParser) -> str:
    if not directory:
        parser.error("Please enter a directory as a positional argument")
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

def validate_format(filename_format_string: str) -> str:
    formatter = string.Formatter()
    for _, field_name, _, _ in formatter.parse(filename_format_string):
        if field_name and field_name not in VALID_FILENAME_OPTIONS:
            raise ValueError(f"The format string provided has invalid keyword: {field_name}") 
    return filename_format_string

def validate_no_posts(posts: list, account: str, post_types: list, update: bool, did: str, restore: str):
    db = Database()
    if restore:
        if did:
            if not db.check_user_exists(did):
                raise ValueError(f"The account: {account} does not exist in the database.")
        elif not posts:
            raise ValueError(f"There are no posts associated with account: {account}, for post_type(s): {post_types}, in the database.")
    if not posts and update:
        raise ValueError(f"Already downloaded the latest post: {account}, for post_type(s): {post_types}")
    elif not posts:    
        raise ValueError(f"There are no posts associated with account: {account}, for post_type(s): {post_types}")

def validate_download(args: argparse.Namespace, parser: argparse.ArgumentParser):
    if args.restore:
        if args.did or args.handle:
            parser.error("If using --restore, then cannot use --did, -d or --handle, should pass the handle/did as a value to --restore")
    else:
        if not args.did and not args.handle:
            parser.error("--did, -d or --handle is required")
        if args.did and args.handle:
            parser.error("--did, -d and --handle are mutually exclusive")
    _validate_post_types(args, parser)

def _validate_post_types(args: argparse.Namespace, parser: argparse.ArgumentParser):
    if not any([args.like, args.post, args.repost]):
        parser.error("At least one flag (--like, --post, --repost) must be set.")