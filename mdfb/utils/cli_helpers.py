import argparse
import re
from collections.abc import Callable
from dataclasses import dataclass

from mdfb.core.resolve_handle import resolve_handle
from mdfb.utils.constants import DEFAULT_THREADS, FeedTypes
from mdfb.utils.database import Database
from mdfb.utils.validation import validate_did


@dataclass
class FetchConfig:
    did: str
    handle: str
    db: Database
    num_threads: int = DEFAULT_THREADS
    restore: bool = False

def is_did(did: str) -> bool:
    """
    is_did: checks if the given did is valid

    Args:
        did (str): Did

    Returns:
        bool: Whether the did is valid

    """
    if not re.search(r"^did:[a-z]+:[a-zA-Z0-9._:%-]*[a-zA-Z0-9._-]$", did):
        return False
    return True


def account_or_did(args: argparse.Namespace, did: str) -> str:
    if args.restore:
        return args.restore
    return args.handle or did


def get_did(args: argparse.Namespace) -> str:
    if args.restore:
        did = None if args.restore is True else args.restore if is_did(args.restore) else resolve_handle(args.restore)
    else:
        did = validate_did(args.did) if args.did else resolve_handle(args.handle)
    return did

def get_post_fetcher(post_type: str, fetch_config: FetchConfig) -> Callable:
    from mdfb.core.get_bookmarks import BookmarkFetcher
    from mdfb.core.get_post_identifiers import PostIdentifierFetcher

    if post_type == FeedTypes.BOOKMARK and not fetch_config.restore:
        fetcher = BookmarkFetcher(fetch_config.handle, fetch_config.db)
        return fetcher.fetch_bookmarks
    fetcher = PostIdentifierFetcher(fetch_config.did, post_type, fetch_config.db, num_threads=fetch_config.num_threads, restore=fetch_config.restore)
    return fetcher.fetch
