from argparse import ArgumentParser
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from mdfb.core.get_post_identifiers import get_post_identifiers
from mdfb.core.fetch_post_details import fetch_post_details
from mdfb.core.download_blobs import download_blobs
from mdfb.core.resolve_handle import resolve_handle
from mdfb.utils.validation import *
from mdfb.utils.helpers import split_list
from mdfb.utils.logging import setup_logging
from mdfb.utils.constants import DEFAULT_THREADS 

def fetch_posts(did: str, limit: int, post_types: dict) -> list[str]:
    post_uris = []
    for post_type, wanted in post_types.items():
        if wanted:
            post_uris.extend(get_post_identifiers(did, limit, post_type))
    return post_uris

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

def main():
    parser = ArgumentParser()

    parser.add_argument("directory", action="store", help="Directory for where all downloaded post will be stored")
    parser.add_argument("-l", "--limit", action="store", required=True, help="The number of posts to be downloaded")  
    parser.add_argument("--like", action="store_true", help="To retreive liked posts")
    parser.add_argument("--post", action="store_true", help="To retreive posts")
    parser.add_argument("--repost", action="store_true", help="To retreive reposts")
    parser.add_argument("--threads", action="store", help="Number of threads, maximum of 3 threads")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--did", action="store", help="The DID associated with the account")
    group.add_argument("--handle", action="store", help="The handle for the account e.g. johnny.bsky.social")
    
    args = parser.parse_args()
    try:
        did = validate_did(args.did) if args.did else resolve_handle(args.handle)
        directory = validate_directory(args.directory)
        limit = validate_limit(args.limit)

        setup_logging(directory)

        num_threads = validate_threads(args.threads) if args.threads else DEFAULT_THREADS
        
        if not any([args.like, args.post, args.repost]):
            raise ValueError("At least one flag (--like, --post, --repost) must be set.")
        
        post_types = {
            "like": args.like,
            "repost": args.repost,
            "post": args.post
        }


        print("Fetching post identifiers...")
        posts = fetch_posts(did, limit, post_types)

        wanted_post_types = [post_type for post_type, wanted in post_types.items() if wanted]
        account = args.handle if args.handle else did
        validate_no_posts(posts, account, wanted_post_types)

        print("Getting post details...")
        post_details = process_posts(posts, num_threads)

        num_of_posts = len(post_details)
        post_links = split_list(post_details, num_threads)

        with tqdm(total=num_of_posts, desc="Downloading files") as progress_bar:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for batch_post_link in post_links:
                    futures.append(executor.submit(download_blobs, batch_post_link, directory, progress_bar))
                    
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    main()  