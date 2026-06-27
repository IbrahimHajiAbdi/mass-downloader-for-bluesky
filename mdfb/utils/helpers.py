from mdfb.core.models import EnrichedPost
from collections.abc import Iterator

def split_list(input_list: list, split_by: int) -> list[list]:
    """
    split_list: splits the list into the given number of equal sized chunks, used for distributing data so that it can be used for threads

    Args:
        input_list (list): input list, length must be >= `split_by`
        split_by (int): number of chunks wanted, must be >= 1

    Returns:
        list[list[str]]: a 2d array of list split into the desired number of chunks, given by `split_by`
    """
    if split_by < 1:
        raise ValueError("Please enter split_by to be greater than 0")
    part_size, remainder = divmod(len(input_list), split_by)

    res = []
    start = 0
    for _ in range(split_by):
        end = start + part_size
        if remainder > 0:
            end += 1
            remainder -= 1
        res.append(input_list[start:end])
        start = end
    return res

def get_chunk(posts: list, chunk_size: int) -> Iterator[list]:
    """
    get_chunk: splits a list into smaller chunks of a specified size.

    Args:
        posts (list): the list to be divided into chunks.
        chunk_size (int): the size of each chunk. Must be >= 1.

    Yields:
        list: a sublist containing up to `chunk_size` elements from the original list.

    Raises:
        ValueError: If `chunk_size` is less than 1.
    """   
    if chunk_size < 1:
        raise ValueError("Please enter a chunk size >= 1")
    for i in range(0, len(posts), chunk_size):
        chunk = posts[i:i+chunk_size]
        yield chunk

def dedupe_posts(posts: list[dict]) -> list[dict]:
    res = {} # poster_post_uri : post
    for post in posts:
        poster_post_uri = post["poster_post_uri"]
        if poster_post_uri in res:
            res[poster_post_uri]["feed_type"].extend(post["feed_type"])
            res[poster_post_uri]["user_post_uri"].extend(post["user_post_uri"])
        else:
            res[poster_post_uri] = post
    return [v for k, v in res.items()]