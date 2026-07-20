import argparse
import contextlib
from unittest.mock import patch

from mdfb import mdfb

DB_DICTS = [
    {
        "user_did": "did:plc:me",
        "user_post_uri": ["at://did:plc:me/app.bsky.bookmark/1"],
        "feed_type": ["bookmark"],
        "poster_post_uri": "at://did:plc:other/app.bsky.feed.post/1",
    }
]


def _args(**overrides):
    base = dict(
        restore=None,
        bookmark=False,
        like=False,
        repost=False,
        post=False,
        media_types=None,
        archive=False,
        update=False,
        limit=None,
        handle=None,
        did=None,
        directory="dir",
        format=None,
        threads=None,
        resource=False,
        include=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


@contextlib.contextmanager
def _patched_pipeline():
    """Stub out everything around the enrichment branch so only the routing decision is exercised."""
    with (
        patch("mdfb.mdfb.get_did", return_value="did:plc:me"),
        patch("mdfb.mdfb.validate_directory", return_value="dir"),
        patch("mdfb.mdfb.setup_logging"),
        patch("mdfb.mdfb.validate_format", return_value=""),
        patch("mdfb.mdfb.validate_limit", return_value=10),
        patch("mdfb.mdfb.validate_no_posts"),
        patch("mdfb.mdfb.account_or_did", return_value="account"),
        patch("mdfb.mdfb.fetch_posts", return_value=DB_DICTS),
        patch("mdfb.mdfb.process_posts", return_value=[]) as process_posts,
        patch("mdfb.mdfb.download_posts") as download_posts,
    ):
        yield process_posts, download_posts


def test_bookmark_restore_enriches_via_process_posts():
    """Regression: restored bookmarks are DB dicts and MUST be enriched, not passed straight to download."""
    parser = argparse.ArgumentParser()
    args = _args(restore="me.bsky.social", bookmark=True)

    with _patched_pipeline() as (process_posts, download_posts):
        mdfb.handle_download(args, parser)

    process_posts.assert_called_once()
    download_posts.assert_called_once()


def test_live_bookmark_skips_process_posts():
    """Live bookmark fetch already returns EnrichedPost objects, so enrichment is (correctly) skipped."""
    parser = argparse.ArgumentParser()
    args = _args(bookmark=True, handle="me.bsky.social", limit="10")

    with _patched_pipeline() as (process_posts, download_posts):
        mdfb.handle_download(args, parser)

    process_posts.assert_not_called()
    download_posts.assert_called_once()
