import json
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from atproto.exceptions import AtProtocolError
from tenacity import RetryError

from mdfb.core import get_post_identifiers, uri_fetcher
from mdfb.core.models import EnrichedPost
from tests.helpers import instant_retry, load_postview

DID = "did:example:1234"


def _enriched(media_type):
    return EnrichedPost(
        response=load_postview("post_image"),
        did="did:plc:xlqcxpk53spbhlypj6wmvvke",
        rkey="r",
        text="t",
        handle="h",
        media_type=media_type,
    )


class TestPostIdentifierFetcher:
    @pytest.fixture
    def list_records_two_likes(self):
        mock_json_response = {
            "records": [
                {
                    "uri": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3ld7z46debo2g",
                    "cid": "bafyreic5s6gfkaogfwljvhxnzxer4xslfopwf26f5qtwakluypzrppamye",
                    "value": {
                        "$type": "app.bsky.feed.like",
                        "subject": {
                            "cid": "bafyreifp4vomoqhxritmilksydl4iixlnqnmwhau4nnprs7dvl4xy6gmqi",
                            "uri": "at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a",
                        },
                        "createdAt": "2024-12-14T00:09:53.185Z",
                    },
                },
                {
                    "uri": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3lbxh76jfuq2y",
                    "cid": "bafyreicksfgvc25tkcobipwirruxyumk2ichbx6fd2zllcki7z6bdzhs3e",
                    "value": {
                        "$type": "app.bsky.feed.like",
                        "subject": {
                            "cid": "bafyreiabo7kerzlewo33l4y6qqdwgmpjhrpi6yagf7fvzn2tepnstn2lie",
                            "uri": "at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e",
                        },
                        "createdAt": "2024-11-27T21:02:56.996Z",
                    },
                },
            ],
            "cursor": "3lbxh76jfuq2y",
        }
        expected = [
            {
                "user_did": DID,
                "user_post_uri": ["at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3ld7z46debo2g"],
                "feed_type": ["like"],
                "poster_post_uri": "at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a",
            },
            {
                "user_did": DID,
                "user_post_uri": ["at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3lbxh76jfuq2y"],
                "feed_type": ["like"],
                "poster_post_uri": "at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e",
            },
        ]
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_response = MagicMock()
            mock_response.model_dump_json.return_value = json.dumps(mock_json_response)
            mock_api_response.return_value = mock_response
            yield {"mock_api_response": mock_api_response, "expected": expected}

    def test_fetch_liked(self, list_records_two_likes):
        fetcher = get_post_identifiers.PostIdentifierFetcher(DID, "like", Mock())
        result = fetcher.fetch(limit=2)

        assert result == list_records_two_likes["expected"]
        list_records_two_likes["mock_api_response"].assert_called_once_with(
            {"collection": "app.bsky.feed.like", "repo": DID, "limit": 2, "cursor": ""}
        )

    def test_fetch_no_likes(self):
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps({"records": []})
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_api_response.return_value = mock_response
            fetcher = get_post_identifiers.PostIdentifierFetcher(DID, "like", Mock())
            assert fetcher.fetch(limit=2) == []


class TestMediaTypesFetch:
    """PostIdentifierFetcher.fetch(media_types=...) routes through MediaTypesFetcher."""

    @pytest.fixture
    def list_records_two_likes(self):
        mock_json_response = {
            "records": [
                {
                    "uri": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3ld7z46debo2g",
                    "cid": "bafyreic5s6gfkaogfwljvhxnzxer4xslfopwf26f5qtwakluypzrppamye",
                    "value": {
                        "$type": "app.bsky.feed.like",
                        "subject": {
                            "cid": "bafyreifp4vomoqhxritmilksydl4iixlnqnmwhau4nnprs7dvl4xy6gmqi",
                            "uri": "at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a",
                        },
                        "createdAt": "2024-12-14T00:09:53.185Z",
                    },
                }
            ],
            "cursor": "3ld7z46debo2g",
        }
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_response = MagicMock()
            mock_response.model_dump_json.return_value = json.dumps(mock_json_response)
            mock_api_response.return_value = mock_response
            yield mock_api_response

    def test_media_types_keeps_matching(self, list_records_two_likes):
        canned = [_enriched(["image"]), _enriched(["text"])]
        # Patch at the use-site: MediaTypesFetcher binds FetchPostDetails at import, and other
        # tests reload the fetch_post_details module, rebinding its class identity.
        with patch("mdfb.core.media_types_fetcher.FetchPostDetails.fetch_post_details", return_value=canned):
            fetcher = get_post_identifiers.PostIdentifierFetcher(DID, "like", Mock())
            result = fetcher.fetch(limit=2, media_types=["image"])

        assert len(result) == 1
        assert result[0].media_type == ["image"]

    def test_media_types_none_match(self, list_records_two_likes):
        canned = [_enriched(["text"])]
        with patch("mdfb.core.media_types_fetcher.FetchPostDetails.fetch_post_details", return_value=canned):
            fetcher = get_post_identifiers.PostIdentifierFetcher(DID, "like", Mock())
            result = fetcher.fetch(limit=2, media_types=["image"])

        assert result == []


class TestURIFetcherRetries:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        with instant_retry(uri_fetcher):
            yield

    @pytest.fixture
    def params(self):
        return {"collection": "app.bsky.feed.like", "repo": DID, "limit": 10, "cursor": ""}

    @pytest.fixture
    def list_records_retry_error(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_api_response.side_effect = [AtProtocolError(), AtProtocolError(), AtProtocolError()]
            yield mock_api_response

    @pytest.fixture
    def list_records_retry_then_succeed(self):
        success_data = ["success!"]
        mock_response = Mock()
        mock_response.model_dump_json.return_value = json.dumps(success_data)
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_api_response.side_effect = [AtProtocolError(), mock_response]
            yield {"mock": mock_api_response, "success_data": success_data}

    def test_exceeds_retries(self, list_records_retry_error, params, caplog):
        fetcher = uri_fetcher.URIFetcher(DID, "like", Mock())
        with caplog.at_level(logging.ERROR), pytest.raises(RetryError):
            fetcher._fetch_with_retry(params, 10)
        assert "Failed to fetch posts: " in caplog.text

    def test_fail_then_succeed(self, list_records_retry_then_succeed, params, caplog):
        fetcher = uri_fetcher.URIFetcher(DID, "like", Mock())
        with caplog.at_level(logging.INFO):
            result = fetcher._fetch_with_retry(params, 10)
        assert result == list_records_retry_then_succeed["success_data"]
        assert (
            "Attempting to fetch up to 10 posts for DID: did:example:1234, feed_type: app.bsky.feed.like" in caplog.text
        )
