from __future__ import annotations

import asyncio
import getpass
import logging
import traceback
from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING

from tqdm.asyncio import tqdm

from mdfb.core.resolve_handle import resolve_handle
from mdfb.utils.cli_helpers import FetchConfig, account_or_did, get_did, get_post_fetcher
from mdfb.utils.config_manager import ConfigManager
from mdfb.utils.constants import DEFAULT_THREADS, MAX_THREADS, FeedTypes
from mdfb.utils.database import Database
from mdfb.utils.helpers import dedupe_posts, split_list
from mdfb.utils.logging import setup_logging, setup_resource_monitoring
from mdfb.utils.validation import (
    validate_directory,
    validate_download,
    validate_format,
    validate_limit,
    validate_no_posts,
    validate_threads,
)

if TYPE_CHECKING:
    from mdfb.core.models import EnrichedPost


async def fetch_posts(
    did: str,
    post_types: dict[str, bool],
    limit: int = 0,
    handle: str = "",
    archive: bool = False,
    update: bool = False,
    media_types: list[str] = [],
    num_threads: int = DEFAULT_THREADS,
    restore: bool = False,
) -> list[dict[str, str]]:

    post_uris = []
    db = Database()
    has_bookmarks = post_types.get(FeedTypes.BOOKMARK, False)
    fetch_config = FetchConfig(did=did, handle=handle, db=db, num_threads=num_threads, restore=restore)

    tasks = []
    async with asyncio.TaskGroup() as tg:
        for post_type, wanted in post_types.items():
            if not wanted:
                continue
            fetch_call = get_post_fetcher(post_type, fetch_config)
            if update:
                if not db.check_user_has_posts(fetch_config.did, post_type):
                    raise ValueError(
                        f"This user has no post in database for feed_type: {post_type}, cannot update as you have not downloaded any post for feed_type: {post_type}."
                    )
                kwargs = dict(archive=archive, update=update, media_types=media_types)
            elif restore and not media_types:
                # TODO: sync db path — left for you to offload (e.g. asyncio.to_thread)
                post_uris.extend(db.restore_posts(did, {post_type: wanted}))
                continue
            else:
                kwargs = dict(limit=limit, archive=archive, update=update, media_types=media_types)

            tasks.append(tg.create_task(fetch_call(**kwargs)))

    for task in tasks:
        post_uris.extend(task.result())
    return dedupe_posts(post_uris) if not (media_types or has_bookmarks) else post_uris


async def process_posts(posts: list, num_threads: int) -> list[EnrichedPost]:
    """
    process_posts: processes the given list of post URIs to get the post details required for downloading, can be threaded

    Args:
        posts (list): list of URIs of the post wanted
        num_threads (int): number of threads

    Returns:
        list[dict]: list of dictionaries that contain post details for each post

    """
    from mdfb.core.fetch_post_details import FetchPostDetails

    posts = split_list(posts, num_threads)
    post_details = []
    fetchPost = FetchPostDetails()
    sem = asyncio.Semaphore(num_threads)
    tasks = []
    async def bounded_download(uris: list[dict[str, str]]):
        async with sem:
            return await fetchPost.fetch_post_details(uris)

    async with asyncio.TaskGroup() as tg:
        for post_batch in posts:
            task = tg.create_task(bounded_download(post_batch))
            tasks.append(task)

    for task in tasks:
        post_details.extend(task.result())
    return post_details


async def download_posts(
    post_link_batches: list[list[EnrichedPost]],
    num_of_posts: int,
    num_threads: int,
    filename_format_string: str,
    directory: str,
    include: str | None = None,
):
    from mdfb.core.download_blobs import DownloadBlobs

    logger = logging.getLogger(__name__)
    downloadBlobs = DownloadBlobs(logger, directory, Database(), filename_format_string, include)
    progress_bar = tqdm(total=num_of_posts, desc="Downloading files")
    completed_downloads = []
    sem = asyncio.Semaphore(num_threads)

    async def bounded_download(posts: list[EnrichedPost], progress_bar: tqdm):
        async with sem:
            await downloadBlobs.download_blobs(posts, progress_bar)

    async with (
        asyncio.TaskGroup() as tg
    ):
        for batch_post_link in post_link_batches:
            task = tg.create_task(bounded_download(batch_post_link, progress_bar))
            completed_downloads.append(task)


async def handle_feed(args: Namespace, parser: ArgumentParser):
    from mdfb.core.get_feed_details import FetchFeedDetails

    directory = validate_directory(args.directory, parser)
    limit = validate_limit(args.limit)
    setup_logging(directory)
    filename_format_string = validate_format(args.format) if args.format else ""
    num_threads = validate_threads(args.threads) if args.threads else DEFAULT_THREADS

    print("Fetching feed details...")

    fetchFeed = FetchFeedDetails(args.handle, args.url)
    posts = await fetchFeed.fetch(limit, args.media_types)

    post_link_batches = split_list(posts, num_threads)

    await download_posts(post_link_batches, len(posts), num_threads, filename_format_string, directory, include=args.include)


def handle_login():
    handle = input("Enter handle: ")
    app_password = getpass.getpass("Enter app password: ")

    ConfigManager(handle).write_credentials(app_password)


def handle_db(args: Namespace, parser: ArgumentParser):
    if getattr(args, "delete_user", False):
        db = Database()
        did = resolve_handle(args.delete_user)
        db.delete_user(did)
        return


async def handle_download(args: Namespace, parser: ArgumentParser):
    did = get_did(args)
    directory = validate_directory(args.directory, parser)
    setup_logging(directory)
    filename_format_string = validate_format(args.format) if args.format else ""
    if args.resource:
        setup_resource_monitoring(directory)

    num_threads = validate_threads(args.threads) if args.threads else DEFAULT_THREADS

    if args.bookmark and (args.like or args.repost or args.post):
        parser.error("--bookmark cannot currently be combined with --like, --repost, or --post.")
    if args.bookmark and (not args.handle and not args.restore):
        parser.error(
            "--bookmark requires --handle (bookmarks require an authenticated session) when not restore from database."
        )

    post_types = {
        FeedTypes.LIKE: args.like,
        FeedTypes.REPOST: args.repost,
        FeedTypes.POST: args.post,
        FeedTypes.BOOKMARK: args.bookmark,
    }

    print("Fetching post identifiers...")
    if args.restore:
        posts = await fetch_posts(
            did,
            post_types,
            archive=True,
            media_types=args.media_types,
            num_threads=num_threads,
            restore=True,
            handle=args.handle,
        )
    elif args.archive:
        posts = await fetch_posts(
            did, post_types, archive=True, media_types=args.media_types, num_threads=num_threads, handle=args.handle
        )
    elif args.update:
        posts = await fetch_posts(
            did,
            post_types,
            archive=True,
            update=True,
            media_types=args.media_types,
            num_threads=num_threads,
            handle=args.handle,
        )
    else:
        limit = validate_limit(args.limit)
        posts = await fetch_posts(
            did, post_types, limit=limit, media_types=args.media_types, num_threads=num_threads, handle=args.handle
        )
    wanted_post_types = [post_type for post_type, wanted in post_types.items() if wanted]
    account = account_or_did(args, did)
    validate_no_posts(posts, account, wanted_post_types, args.update, did, args.restore)

    if args.media_types or (args.bookmark and not args.restore):
        post_details = posts
    else:
        print("Getting post details...")
        post_details = await process_posts(posts, num_threads)

    num_of_posts = len(post_details)
    post_links = split_list(post_details, num_threads)

    await download_posts(post_links, num_of_posts, num_threads, filename_format_string, directory, args.include)


async def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers(dest="subcommand", required=False)

    common_parser = ArgumentParser(add_help=False)

    common_parser.add_argument(
        "--threads", "-t", action="store", help=f"Number of threads, maximum of {MAX_THREADS} threads"
    )
    common_parser.add_argument(
        "--format",
        "-f",
        action="store",
        help="Format string for filename e.g '{RKEY}_{DID}'. Valid keywords are: [RKEY, HANDLE, TEXT, DISPLAY_NAME, DID]",
    )
    common_parser.add_argument("--did", "-d", action="store", help="The DID associated with the account")
    common_parser.add_argument("--handle", action="store", help="The handle for the account e.g. johnny.bsky.social")
    common_parser.add_argument(
        "--resource", "-r", action="store_true", help="Logs resource usage of memory and cpu at 5 second intervals"
    )

    database_parser = subparsers.add_parser("db", help="Manage the database", parents=[common_parser])
    database_parser.add_argument("--delete_user", action="store", help="Delete all posts from this user")
    database_parser.add_argument(
        "directory",
        nargs="?",
        action="store",
        default="",
        help="Directory for where all downloaded post will be stored",
    )

    download_parser = subparsers.add_parser("download", help="Download posts", parents=[common_parser])
    download_parser.add_argument(
        "directory", action="store", help="Directory for where all downloaded post will be stored"
    )
    download_parser.add_argument(
        "--media-types",
        choices=["image", "video", "text"],
        nargs="+",
        help="Only download posts that contain this type of media",
    )
    download_parser.add_argument(
        "--include",
        "-i",
        nargs=1,
        choices=["json", "media"],
        help="Whether to include the json of the post, or media attached to the post",
    )
    download_parser.add_argument("--like", action="store_true", help="To retrieve liked posts")
    download_parser.add_argument("--post", action="store_true", help="To retrieve posts")
    download_parser.add_argument("--repost", action="store_true", help="To retrieve reposts")
    download_parser.add_argument("--bookmark", action="store_true", help="To retrieve bookmarked posts")

    group_archive_limit = download_parser.add_mutually_exclusive_group(required=True)
    group_archive_limit.add_argument("--limit", "-l", action="store", help="The number of posts to be downloaded")
    group_archive_limit.add_argument(
        "--restore", nargs="?", const=True, help="Restore all posts in the database or for those for a specified handle"
    )
    group_archive_limit.add_argument(
        "--archive", action="store_true", help="To archive all posts of the specified types"
    )
    group_archive_limit.add_argument(
        "--update", "-u", action="store_true", help="Downloads latest posts that haven't been downloaded"
    )

    login_parser = subparsers.add_parser("login", help="Login", parents=[common_parser])

    feed_parser = subparsers.add_parser("feed", help="Download posts from specified feed", parents=[common_parser])
    feed_parser.add_argument(
        "--limit", "-l", action="store", help="The number of posts to be downloaded", required=True
    )
    feed_parser.add_argument("--url", action="store", help="The URL for the feed", required=True)
    feed_parser.add_argument("directory", action="store", help="Directory for where all downloaded post will be stored")
    feed_parser.add_argument(
        "--media-types",
        choices=["image", "video", "text"],
        nargs="+",
        help="Only download posts that contain this type of media",
    )
    feed_parser.add_argument(
        "--include",
        "-i",
        nargs=1,
        choices=["json", "media"],
        help="Whether to include the json of the post, or media attached to the post",
    )

    args = parser.parse_args()
    try:
        if args.subcommand == "download":
            validate_download(args, parser)
            await handle_download(args, parser)
        elif args.subcommand == "db":
            handle_db(args, parser)
        elif args.subcommand == "login":
            handle_login()
        elif args.subcommand == "feed":
            await handle_feed(args, parser)

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


def cli():
    """Synchronous entry point for the ``mdfb`` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
