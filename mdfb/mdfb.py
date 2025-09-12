import logging
import traceback

from argparse import ArgumentParser, Namespace
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from mdfb.core.get_post_identifiers import get_post_identifiers 
from mdfb.core.fetch_post_details import fetch_post_details
from mdfb.core.download_blobs import download_blobs
from mdfb.core.resolve_handle import resolve_handle
from mdfb.utils.validation import validate_database, validate_directory, validate_download, validate_format, validate_limit, validate_no_posts, validate_threads
from mdfb.utils.helpers import split_list, dedupe_posts
from mdfb.utils.cli_helpers import account_or_did, get_did 
from mdfb.utils.database import connect_db, delete_user, check_user_has_posts, restore_posts
from mdfb.utils.logging import setup_logging, setup_resource_monitoring
from mdfb.utils.constants import DEFAULT_THREADS, MAX_THREADS 

def fetch_posts(did: str, post_types: dict[str, bool], limit: int = 0, archive: bool = False, update: bool = False, media_types: list[str] = None, num_threads: int = 1, restore: bool = False) -> list[dict[str, str]]:
    post_uris = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for post_type, wanted in post_types.items():
            if wanted:
                if update:
                    if check_user_has_posts(connect_db().cursor(), did, post_type):
                        futures.append(executor.submit(get_post_identifiers, did, post_type, archive=archive, update=update, media_types=media_types, num_threads=num_threads))
                    else:
                        raise ValueError(f"This user has no post in database for feed_type: {post_type}, cannot update as you have not downloaded any post for feed_type: {post_type}.")
                else:
                    if media_types:
                        futures.append(executor.submit(get_post_identifiers, did, post_type, media_types, limit=limit, archive=archive, update=update, num_threads=num_threads, restore=restore))
                    elif restore:
                        futures.append(executor.submit(restore_posts, did, {post_type: wanted}))
                    else:
                        futures.append(executor.submit(get_post_identifiers, did, post_type, limit=limit, archive=archive, update=update))
        for future in as_completed(futures):
            post_uris.extend(future.result())
    return dedupe_posts(post_uris)

def process_posts(posts: list, num_threads: int) -> list[dict]:
    """
    process_posts: processes the given list of post URIs to get the post details required for downloading, can be threaded 

    Args:
        posts (list): list of URIs of the post wanted
        num_threads (int): number of threads 

    Returns:
        list[dict]: list of dictionaries that contain post details for each post
    """
    posts = split_list(posts, num_threads)
    post_details = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for post_batch in posts:
            futures.append(executor.submit(fetch_post_details, post_batch))
        for future in as_completed(futures):
            post_details.extend(future.result())
    return post_details

def download_posts(post_links: list[dict], num_of_posts: int, num_threads: int, filename_format_string: str, directory: str, include: str = None):
    logger = logging.getLogger(__name__)
    with tqdm(total=num_of_posts, desc="Downloading files") as progress_bar:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for batch_post_link in post_links:
                if not filename_format_string:
                    futures.append(executor.submit(download_blobs, batch_post_link, directory, progress_bar, include=include))
                else:
                    futures.append(executor.submit(download_blobs, batch_post_link, directory, progress_bar, filename_format_string, include=include))
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in thread: {e}")
                    logger.error(f"Error in thread: {e}", exc_info=True)
                    
def handle_db(args: Namespace, parser: ArgumentParser):
    validate_database()
    if getattr(args, "delete_user", False):
        did = resolve_handle(args.delete_user)
        delete_user(did)
        return 

def handle_download(args: Namespace, parser: ArgumentParser):
    did = get_did(args)
    directory = validate_directory(args.directory, parser)
    filename_format_string = validate_format(args.format) if args.format else ""
    setup_logging(directory)
    if args.resource:
        setup_resource_monitoring(directory)
    validate_database()

    num_threads = validate_threads(args.threads) if args.threads else DEFAULT_THREADS
    
    post_types = {
        "like": args.like,
        "repost": args.repost,
        "post": args.post
    }

    print("Fetching post identifiers...")
    if args.restore:
        posts = fetch_posts(did, post_types, archive=True, media_types=args.media_types, num_threads=num_threads, restore=True)
    elif args.archive:
        posts = fetch_posts(did, post_types, archive=True, media_types=args.media_types, num_threads=num_threads)
    elif args.update:
        posts = fetch_posts(did, post_types, archive=True, update=True, media_types=args.media_types, num_threads=num_threads)
    else:
        limit = validate_limit(args.limit)
        posts = fetch_posts(did, post_types, limit=limit, media_types=args.media_types, num_threads=num_threads)
    wanted_post_types = [post_type for post_type, wanted in post_types.items() if wanted]
    account = account_or_did(args, did)
    validate_no_posts(posts, account, wanted_post_types, args.update, did, args.restore)

    if args.media_types:
        post_details = posts
    else:
        print("Getting post details...")
        post_details = process_posts(posts, num_threads)

    num_of_posts = len(post_details)
    post_links = split_list(post_details, num_threads)

    download_posts(post_links, num_of_posts, num_threads, filename_format_string, directory, args.include)

def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers(dest="subcommand", required=False)

    common_parser = ArgumentParser(add_help=False)

    common_parser.add_argument("--like", action="store_true", help="To retreive liked posts")
    common_parser.add_argument("--post", action="store_true", help="To retreive posts")
    common_parser.add_argument("--repost", action="store_true", help="To retreive reposts")
    common_parser.add_argument("--threads", "-t", action="store", help=f"Number of threads, maximum of {MAX_THREADS} threads")
    common_parser.add_argument("--format", "-f", action="store", help="Format string for filename e.g '{RKEY}_{DID}'. Valid keywords are: [RKEY, HANDLE, TEXT, DISPLAY_NAME, DID]")
    common_parser.add_argument("--did", "-d", action="store", help="The DID associated with the account")
    common_parser.add_argument("--handle", action="store", help="The handle for the account e.g. johnny.bsky.social")
    common_parser.add_argument("--resource", "-r", action="store_true", help="Logs resource usage of memory and cpu at 5 second intervals")

    database_parser = subparsers.add_parser("db", help="Manage the database", parents=[common_parser])
    database_parser.add_argument("--delete_user", action="store", help="Delete all posts from this user")
    database_parser.add_argument("directory", nargs="?", action="store", default="", help="Directory for where all downloaded post will be stored")

    download_parser = subparsers.add_parser("download", help="Download posts", parents=[common_parser])
    download_parser.add_argument("directory", action="store", help="Directory for where all downloaded post will be stored")
    download_parser.add_argument("--media-types", choices=["image", "video", "text"], nargs="+", help="Only download posts that contain this type of media")    
    download_parser.add_argument("--include", "-i", nargs=1, choices=["json", "media"], help="Whether to include the json of the post, or media attached to the post")

    group_archive_limit = download_parser.add_mutually_exclusive_group(required=True)
    group_archive_limit.add_argument("--limit", "-l", action="store", help="The number of posts to be downloaded") 
    group_archive_limit.add_argument("--restore", nargs="?", const=True, help="Restore all posts in the database or for those for a specified handle")
    group_archive_limit.add_argument("--archive", action="store_true", help="To archive all posts of the specified types")
    group_archive_limit.add_argument("--update", "-u", action="store_true", help="Downloads latest posts that haven't been downloaded")
    args = parser.parse_args()
    try:
        if args.subcommand == "download":
            validate_download(args, parser)
            handle_download(args, parser)
        elif args.subcommand == "db":
            handle_db(args, parser)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        
if __name__ == "__main__":
    main()  