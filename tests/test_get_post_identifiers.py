import json
from unittest.mock import MagicMock, Mock, patch
from tenacity import stop_after_attempt, retry, wait_fixed, RetryError
import pytest
import logging
from atproto.exceptions import AtProtocolError
from mdfb.core import get_post_identifiers

class TestGetPostIdentifiers:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        fast_retry = retry(wait=wait_fixed(0), stop=stop_after_attempt(2))
        
        with patch('tenacity.retry', return_value=fast_retry):
            import importlib
            from mdfb.core import get_post_identifiers
            
            importlib.reload(get_post_identifiers)
            yield

    @pytest.fixture(scope="class")
    def get_post_api_response(self):
        mock_json_response = {
            "records": [
                {
                    "uri": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3ld7z46debo2g",
                    "cid": "bafyreic5s6gfkaogfwljvhxnzxer4xslfopwf26f5qtwakluypzrppamye",
                    "value": {
                        "$type": "app.bsky.feed.like",
                        "subject": {
                            "cid": "bafyreifp4vomoqhxritmilksydl4iixlnqnmwhau4nnprs7dvl4xy6gmqi",
                            "uri": "at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a"
                        },
                        "createdAt": "2024-12-14T00:09:53.185Z"
                    }
                },
                {
                    "uri": "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3lbxh76jfuq2y",
                    "cid": "bafyreicksfgvc25tkcobipwirruxyumk2ichbx6fd2zllcki7z6bdzhs3e",
                    "value": {
                        "$type": "app.bsky.feed.like",
                        "subject": {
                            "cid": "bafyreiabo7kerzlewo33l4y6qqdwgmpjhrpi6yagf7fvzn2tepnstn2lie",
                            "uri": "at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e"
                        },
                        "createdAt": "2024-11-27T21:02:56.996Z"
                    }
                }
            ],
            "cursor": "3lbxh76jfuq2y"
        }
        expected = [{'user_did': 'did:example:1234', 'user_post_uri': ['at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3ld7z46debo2g'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a'}, {'user_did': 'did:example:1234', 'user_post_uri': ['at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.like/3lbxh76jfuq2y'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e'}]
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_response = MagicMock()
            mock_response.model_dump_json.return_value = json.dumps(mock_json_response)
            mock_api_response.return_value = mock_response
            yield {
                "mock_api_response": mock_api_response,
                "expected": expected
            }

    @pytest.fixture(scope="class")
    def successful_response_media_types(self, get_post_api_response):
        mock_fetch_post_response = [{'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lrjgrrwsdg2z'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a', 'author': {'did': 'did:plc:xlqcxpk53spbhlypj6wmvvke', 'handle': 'popbase.tv', 'associated': {'chat': {'allow_incoming': 'all', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:xlqcxpk53spbhlypj6wmvvke/bafkreicieqzk3twxj6zeyd7gpm637zib277rkyciorvfu25whjhzn3542u@jpeg', 'created_at': '2024-09-03T22:04:10.910Z', 'display_name': 'Pop Base', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreifp4vomoqhxritmilksydl4iixlnqnmwhau4nnprs7dvl4xy6gmqi', 'indexed_at': '2024-12-13T07:44:21.553Z', 'record': {'created_at': '2024-12-13T07:44:19.946Z', 'text': 'Bluesky has passed a milestone of 25 MILLION users.', 'embed': {'images': [{'alt': 'Landscape image of the Bluesky logo.', 'image': {'mime_type': 'image/jpeg', 'size': 82140, 'ref': {'link': 'bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu'}, 'py_type': 'blob'}, 'aspect_ratio': {'height': 683, 'width': 1290, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#image'}], 'py_type': 'app.bsky.embed.images'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a', 'embed': {'images': [{'alt': 'Landscape image of the Bluesky logo.', 'fullsize': 'https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:xlqcxpk53spbhlypj6wmvvke/bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu@jpeg', 'thumb': 'https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:xlqcxpk53spbhlypj6wmvvke/bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu@jpeg', 'aspect_ratio': {'height': 683, 'width': 1290, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#viewImage'}], 'py_type': 'app.bsky.embed.images#view'}, 'labels': [], 'like_count': 8577, 'quote_count': 109, 'reply_count': 128, 'repost_count': 677, 'threadgate': None, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}, {'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lrjgroyvx42x'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e', 'author': {'did': 'did:plc:vc7f4oafdgxsihk4cry2xpze', 'handle': 'jcsalterego.bsky.social', 'associated': {'chat': {'allow_incoming': 'following', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:vc7f4oafdgxsihk4cry2xpze/bafkreicwxwecqiko2rwwln5y3fqqb2zx6wfg5rxf5r7lukakkq2slqy5hy@jpeg', 'created_at': '2023-04-23T20:11:04.375Z', 'display_name': 'Jerry Chen', 'labels': [{'cts': '1970-01-01T00:00:00.000Z', 'src': 'did:plc:vc7f4oafdgxsihk4cry2xpze', 'uri': 'at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.actor.profile/self', 'val': '!no-unauthenticated', 'cid': 'bafyreidfiuv3c22vliyu2onazf23zrp35rr7i3upsqa2dsn5cqimmlgugm', 'exp': None, 'neg': None, 'sig': None, 'ver': None, 'py_type': 'com.atproto.label.defs#label'}], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreiabo7kerzlewo33l4y6qqdwgmpjhrpi6yagf7fvzn2tepnstn2lie', 'indexed_at': '2024-11-27T20:07:29.966Z', 'record': {'created_at': '2024-11-27T20:07:29.775Z', 'text': 'no i will not pay $29.99/mo to know which one of my posts made it into the bsky slack. i will pay much, much more', 'embed': None, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e', 'embed': None, 'labels': [], 'like_count': 1211, 'quote_count': 4, 'reply_count': 29, 'repost_count': 45, 'threadgate': {'cid': 'bafyreigo3mzmgz665jqzngjjuxm3hxnmbvkkqs37lxvxt722ycfjv73dbq', 'lists': [], 'record': {'created_at': '2024-11-28T18:04:38.197Z', 'post': 'at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.post/3lbxe3z66hk2e', 'allow': None, 'hidden_replies': ['at://did:plc:3cbrfca7okiytbjbpdu3cmgz/app.bsky.feed.post/3lbznkdbosk2v'], 'py_type': 'app.bsky.feed.threadgate'}, 'uri': 'at://did:plc:vc7f4oafdgxsihk4cry2xpze/app.bsky.feed.threadgate/3lbxe3z66hk2e', 'py_type': 'app.bsky.feed.defs#threadgateView'}, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}]
        expected = [{'rkey': '3ld6bzuenjs2a', 'text': 'Bluesky has passed a milestone of 25 MILLION users.', 'response': {'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lrjgrrwsdg2z'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a', 'author': {'did': 'did:plc:xlqcxpk53spbhlypj6wmvvke', 'handle': 'popbase.tv', 'associated': {'chat': {'allow_incoming': 'all', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:xlqcxpk53spbhlypj6wmvvke/bafkreicieqzk3twxj6zeyd7gpm637zib277rkyciorvfu25whjhzn3542u@jpeg', 'created_at': '2024-09-03T22:04:10.910Z', 'display_name': 'Pop Base', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreifp4vomoqhxritmilksydl4iixlnqnmwhau4nnprs7dvl4xy6gmqi', 'indexed_at': '2024-12-13T07:44:21.553Z', 'record': {'created_at': '2024-12-13T07:44:19.946Z', 'text': 'Bluesky has passed a milestone of 25 MILLION users.', 'embed': {'images': [{'alt': 'Landscape image of the Bluesky logo.', 'image': {'mime_type': 'image/jpeg', 'size': 82140, 'ref': {'link': 'bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu'}, 'py_type': 'blob'}, 'aspect_ratio': {'height': 683, 'width': 1290, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#image'}], 'py_type': 'app.bsky.embed.images'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a', 'embed': {'images': [{'alt': 'Landscape image of the Bluesky logo.', 'fullsize': 'https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:xlqcxpk53spbhlypj6wmvvke/bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu@jpeg', 'thumb': 'https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:xlqcxpk53spbhlypj6wmvvke/bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu@jpeg', 'aspect_ratio': {'height': 683, 'width': 1290, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#viewImage'}], 'py_type': 'app.bsky.embed.images#view'}, 'labels': [], 'like_count': 8577, 'quote_count': 109, 'reply_count': 128, 'repost_count': 677, 'threadgate': None, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}, 'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lrjgrrwsdg2z'], 'poster_post_uri': 'at://did:plc:xlqcxpk53spbhlypj6wmvvke/app.bsky.feed.post/3ld6bzuenjs2a', 'feed_type': ['like'], 'did': 'did:plc:xlqcxpk53spbhlypj6wmvvke', 'handle': 'popbase.tv', 'display_name': 'Pop Base', 'media_type': ['image'], 'images_cid': ['bafkreifma6v5wt6ml4srjfzd3ayd743kg2kjwvu2rnursohhjffuypqhhu'], 'mime_type': 'image/jpeg'}]
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response, \
            patch("mdfb.core.fetch_post_details._merge_uri_chunk_to_records") as mock_merged:
            mock_response = Mock()
            mock_response.model_dump_json.return_value = json.dumps(mock_fetch_post_response)
            mock_merged.return_value = mock_fetch_post_response
            mock_api_response.return_value = mock_response
            yield {
                "mock_api_response": mock_api_response,
                "expected": expected
            }
    
    @pytest.fixture(scope="class")
    def non_response_media_types(self, get_post_api_response):
        mock_fetch_post_response = []
        expected = []
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response, \
            patch("mdfb.core.fetch_post_details._merge_uri_chunk_to_records") as mock_merged:
            mock_response = Mock()
            mock_response.model_dump_json.return_value = json.dumps(mock_fetch_post_response)
            mock_merged.return_value = mock_fetch_post_response
            mock_api_response.return_value = mock_response
            yield {
                "mock_api_response": mock_api_response,
                "expected": expected
            }


    @pytest.fixture(scope="class")
    def api_response_retry_error(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_api_response.side_effect = [
                AtProtocolError(),
                AtProtocolError(),
                AtProtocolError()
            ]
            yield mock_api_response

    @pytest.fixture(scope="class")
    def api_response_retry_then_succeed(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            success_data = ["success!"]
            mock_response = Mock()
            mock_response.model_dump_json.return_value = json.dumps(success_data)
            mock_api_response.return_value = mock_response
            mock_api_response.side_effect = [
                AtProtocolError(),
                mock_response
            ]
            yield {
                'mock': mock_api_response,
                'success_data': success_data
            }  

    def test_get_post_identifiers_liked(self, get_post_api_response):
        fetcher = get_post_identifiers.PostIdentifierFetcher("did:example:1234", "like")
        result = fetcher.fetch(limit=2)
        assert result == get_post_api_response["expected"]
        get_post_api_response["mock_api_response"].assert_called_once_with({'collection': 'app.bsky.feed.like', 'repo': 'did:example:1234', 'limit': 2, 'cursor': ''})

    def test_get_post_identifiers_no_likes(self):
        mock_json_response = {
            "records": []
        }
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps(mock_json_response)
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoRepoNamespace.list_records") as mock_api_response:
            mock_api_response.return_value = mock_response
            fetcher = get_post_identifiers.PostIdentifierFetcher("did:example:1234", "like")
            result = fetcher.fetch(limit=2)
            assert result == []

    def test_get_post_identifiers_media_types_video(self, successful_response_media_types):
        fetcher = get_post_identifiers.PostIdentifierFetcher("did:example:1234", "like")
        result = fetcher.fetch(limit=2, media_types=["image"])

        assert len(result) == 1
        assert result == successful_response_media_types["expected"]        

    def test_get_post_identifiers_media_types_non(self, non_response_media_types):
        fetcher = get_post_identifiers.PostIdentifierFetcher("did:example:1234", "like")
        result = fetcher.fetch(limit=2, media_types=["image"])

        assert len(result) == 0
        assert result == non_response_media_types["expected"]        


    def test_get_post_identifiers_exceeds_retries(self, api_response_retry_error, caplog):
        logger = logging.getLogger('mdfb.core.get_post_identifiers')  
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RetryError):
                get_post_identifiers._get_post_identifiers_with_retires({}, Mock(), 10, logger)
        assert "Failure to fetch posts: " in caplog.text
    
    def test_get_post_identifiers_fail_succeed(self, api_response_retry_then_succeed, caplog):    
        logger = logging.getLogger('mdfb.core.get_post_identifiers')  
        with caplog.at_level(logging.INFO):
            res = get_post_identifiers._get_post_identifiers_with_retires({
                "repo": "test repo",
                "collection": "test collection",
            }, Mock(), 10, logger)  
        assert res == api_response_retry_then_succeed["success_data"]
        assert "Attempting to fetch up to 10 posts for DID: test repo, feed_type: test collection" in caplog.text
        