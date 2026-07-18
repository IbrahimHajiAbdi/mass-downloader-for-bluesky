from enum import StrEnum

MAX_THREADS = 3
DELAY = 0.25  # in seconds
DEFAULT_THREADS = 1
RETRIES = 5
EXP_WAIT_MULTIPLIER = 1
EXP_WAIT_MAX = 16
EXP_WAIT_MIN = 0.5
VALID_FILENAME_OPTIONS = {"RKEY", "HANDLE", "DID", "TEXT", "DISPLAY_NAME"}


class FeedTypes(StrEnum):
    LIKE = "like"
    REPOST = "repost"
    POST = "post"
    BOOKMARK = "bookmark"
