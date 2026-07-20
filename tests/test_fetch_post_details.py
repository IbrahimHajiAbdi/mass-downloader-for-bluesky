import logging
from unittest.mock import Mock, patch

import pytest
from atproto.exceptions import AtProtocolError
from atproto_client.models.app.bsky.feed.get_posts import Response as GetPostsResponse
from tenacity import RetryError

from mdfb.core import fetch_post_details
from tests.helpers import instant_retry, load_postview

IMAGE_URI = "at://did:plc:3eatnvb2dim4l7fiwln5wow6/app.bsky.feed.post/3lqwz2kuzg22s"
IMAGE_CID = "bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze"


def _image_uri_chunk():
    return [
        {
            "poster_post_uri": IMAGE_URI,
            "user_did": "did:plc:u6iyyil77bqv5fknwauj3tfk",
            "user_post_uri": ["at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.repost/3lqx3fnspgj2s"],
            "feed_type": ["repost"],
        }
    ]


class TestFetchPostDetails:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        with instant_retry(fetch_post_details):
            yield

    @pytest.fixture
    def get_posts_returns_image(self):
        response = GetPostsResponse(posts=[load_postview("post_image")])
        with patch(
            "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts", return_value=response
        ) as mock_get_posts:
            yield mock_get_posts

    @pytest.fixture
    def get_posts_returns_empty(self):
        response = GetPostsResponse(posts=[])
        with patch(
            "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts", return_value=response
        ) as mock_get_posts:
            yield mock_get_posts

    def test_fetch_post_details(self, get_posts_returns_image):
        result = fetch_post_details.FetchPostDetails().fetch_post_details(_image_uri_chunk())

        assert len(result) == 1
        post = result[0]
        assert post.rkey == "3lqwz2kuzg22s"
        assert post.did == "did:plc:3eatnvb2dim4l7fiwln5wow6"
        assert post.handle == "dailybunnies.bsky.social"
        assert post.media_type == ["image"]
        assert post.images_cid == [IMAGE_CID]
        assert post.mime_type == "image/jpeg"
        # enrichment from the uri chunk
        assert post.feed_type == ["repost"]
        assert post.user_did == "did:plc:u6iyyil77bqv5fknwauj3tfk"
        assert post.poster_post_uri == IMAGE_URI

    def test_fetch_post_details_no_uris(self):
        assert fetch_post_details.FetchPostDetails().fetch_post_details([]) == []

    def test_fetch_post_details_deleted_post(self, get_posts_returns_empty, caplog):
        with caplog.at_level(logging.INFO):
            result = fetch_post_details.FetchPostDetails().fetch_post_details(_image_uri_chunk())
        assert result == []
        assert "The post associated with this URI is missing/deleted:" in caplog.text


class TestGetPostDetails:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        with instant_retry(fetch_post_details):
            yield

    @pytest.fixture
    def get_posts_retry_error(self):
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_get_posts:
            mock_get_posts.side_effect = [AtProtocolError(), AtProtocolError(), AtProtocolError()]
            yield mock_get_posts

    @pytest.fixture
    def get_posts_retry_then_succeed(self):
        success_data = GetPostsResponse(posts=[])
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_get_posts:
            mock_get_posts.side_effect = [AtProtocolError(), success_data]
            yield {"mock": mock_get_posts, "success_data": success_data}

    @pytest.fixture
    def get_posts_succeeds(self):
        success_data = GetPostsResponse(posts=[])
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_get_posts:
            mock_get_posts.side_effect = [success_data]
            yield {"mock": mock_get_posts, "success_data": success_data}

    def test_get_post_details_exceeds_retries(self, get_posts_retry_error):
        with pytest.raises(RetryError):
            fetch_post_details.FetchPostDetails()._get_post_details([{"poster_post_uri": ""}])

    def test_get_post_details_with_retries_success(self, get_posts_succeeds):
        result = fetch_post_details.FetchPostDetails()._get_post_details_with_retries([{"poster_post_uri": ""}])
        assert result == get_posts_succeeds["success_data"]

    def test_get_post_details_with_retries_failure(self, get_posts_retry_error, caplog):
        uris = [{"poster_post_uri": ""}]
        with caplog.at_level(logging.ERROR):
            result = fetch_post_details.FetchPostDetails()._get_post_details_with_retries(uris)
        assert result is None
        assert f"Failure to fetch records from the URIs: {uris}" in caplog.text

    def test_get_post_details_retries_then_succeeds(self, get_posts_retry_then_succeed, caplog):
        with caplog.at_level(logging.ERROR):
            result = fetch_post_details.FetchPostDetails()._get_post_details_with_retries([{"poster_post_uri": ""}])
        assert result == get_posts_retry_then_succeed["success_data"]
        assert "Error occurred fetching records from URIs:" in caplog.text


class TestMergeUriChunkToRecords:
    def test_merge_matches_by_poster_uri(self):
        uri_chunk = [{"poster_post_uri": "example_uri_1"}, {"poster_post_uri": "example_uri_2"}]
        records = [Mock(uri="example_uri_1"), Mock(uri="example_uri_2")]

        result = fetch_post_details.FetchPostDetails()._merge_uri_chunk_to_records(uri_chunk, records)

        assert result == [(records[0], uri_chunk[0]), (records[1], uri_chunk[1])]

    def test_merge_skips_unmatched(self):
        uri_chunk = [{"poster_post_uri": "example_uri_1"}]
        records = [Mock(uri="no_match")]

        assert fetch_post_details.FetchPostDetails()._merge_uri_chunk_to_records(uri_chunk, records) == []
