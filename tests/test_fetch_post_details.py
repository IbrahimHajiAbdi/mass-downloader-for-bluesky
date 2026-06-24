import json
import logging
from unittest.mock import Mock, patch
import pytest
from tenacity import RetryError, stop_after_attempt, retry, wait_fixed
from atproto.exceptions import AtProtocolError
from mdfb.core import fetch_post_details

class TestFetchPostDetails:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        fast_retry = retry(wait=wait_fixed(0), stop=stop_after_attempt(2))
        
        with patch('tenacity.retry', return_value=fast_retry):
            import importlib
            from mdfb.core import fetch_post_details

            importlib.reload(fetch_post_details)
            yield

    @pytest.fixture(scope="class")
    def api_response(self):
        return {
            "success": {
                "return": [{'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lr4iyr7fgu2q'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'author': {'did': 'did:plc:vpkdwwdia5etkdsuvsewtlws', 'handle': 'inkpixels.bsky.social', 'associated': {'chat': {'allow_incoming': 'following', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:vpkdwwdia5etkdsuvsewtlws/bafkreiauvzci74nrfoxhkfgd3mo6h75ejmzpxpyxlkbg2d5shflhy2ugmu@jpeg', 'created_at': '2023-08-20T15:22:50.198Z', 'display_name': 'ink', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreidhuc5hv3iiq26e6citq2d77xl5gwsf22mp6qpwtl73hdkjqy3jsa', 'indexed_at': '2025-06-06T16:11:06.061Z', 'record': {'created_at': '2025-06-06T16:11:02.304Z', 'text': '11 colors, pixelart', 'embed': {'images': [{'alt': '', 'image': {'mime_type': 'image/jpeg', 'size': 631615, 'ref': {'link': 'bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei'}, 'py_type': 'blob'}, 'aspect_ratio': {'height': 570, 'width': 960, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#image'}], 'py_type': 'app.bsky.embed.images'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'embed': {'images': [{'alt': '', 'fullsize': 'https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:vpkdwwdia5etkdsuvsewtlws/bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei@jpeg', 'thumb': 'https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:vpkdwwdia5etkdsuvsewtlws/bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei@jpeg', 'aspect_ratio': {'height': 570, 'width': 960, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#viewImage'}], 'py_type': 'app.bsky.embed.images#view'}, 'labels': [], 'like_count': 4621, 'quote_count': 11, 'reply_count': 41, 'repost_count': 940, 'threadgate': {'cid': 'bafyreig7tcabkvv5erg4subslzkwmrk5ge6zmjz4k7re2dhuldf3wlksfa', 'lists': [], 'record': {'created_at': '2025-06-07T09:11:01.662Z', 'post': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'allow': None, 'hidden_replies': ['at://did:plc:bkd55nd44ddocqyv5cbxa3hq/app.bsky.feed.post/3lqyt2fow6s2j'], 'py_type': 'app.bsky.feed.threadgate'}, 'uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.threadgate/3lqx7wzy7c227', 'py_type': 'app.bsky.feed.defs#threadgateView'}, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}],
                "expected": [{'rkey': '3lqx7wzy7c227', 'text': '11 colors, pixelart', 'response': {'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lr4iyr7fgu2q'], 'feed_type': ['like'], 'poster_post_uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'author': {'did': 'did:plc:vpkdwwdia5etkdsuvsewtlws', 'handle': 'inkpixels.bsky.social', 'associated': {'chat': {'allow_incoming': 'following', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:vpkdwwdia5etkdsuvsewtlws/bafkreiauvzci74nrfoxhkfgd3mo6h75ejmzpxpyxlkbg2d5shflhy2ugmu@jpeg', 'created_at': '2023-08-20T15:22:50.198Z', 'display_name': 'ink', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreidhuc5hv3iiq26e6citq2d77xl5gwsf22mp6qpwtl73hdkjqy3jsa', 'indexed_at': '2025-06-06T16:11:06.061Z', 'record': {'created_at': '2025-06-06T16:11:02.304Z', 'text': '11 colors, pixelart', 'embed': {'images': [{'alt': '', 'image': {'mime_type': 'image/jpeg', 'size': 631615, 'ref': {'link': 'bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei'}, 'py_type': 'blob'}, 'aspect_ratio': {'height': 570, 'width': 960, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#image'}], 'py_type': 'app.bsky.embed.images'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'embed': {'images': [{'alt': '', 'fullsize': 'https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:vpkdwwdia5etkdsuvsewtlws/bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei@jpeg', 'thumb': 'https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:vpkdwwdia5etkdsuvsewtlws/bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei@jpeg', 'aspect_ratio': {'height': 570, 'width': 960, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#viewImage'}], 'py_type': 'app.bsky.embed.images#view'}, 'labels': [], 'like_count': 4621, 'quote_count': 11, 'reply_count': 41, 'repost_count': 940, 'threadgate': {'cid': 'bafyreig7tcabkvv5erg4subslzkwmrk5ge6zmjz4k7re2dhuldf3wlksfa', 'lists': [], 'record': {'created_at': '2025-06-07T09:11:01.662Z', 'post': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'allow': None, 'hidden_replies': ['at://did:plc:bkd55nd44ddocqyv5cbxa3hq/app.bsky.feed.post/3lqyt2fow6s2j'], 'py_type': 'app.bsky.feed.threadgate'}, 'uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.threadgate/3lqx7wzy7c227', 'py_type': 'app.bsky.feed.defs#threadgateView'}, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}, 'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.like/3lr4iyr7fgu2q'], 'poster_post_uri': 'at://did:plc:vpkdwwdia5etkdsuvsewtlws/app.bsky.feed.post/3lqx7wzy7c227', 'feed_type': ['like'], 'did': 'did:plc:vpkdwwdia5etkdsuvsewtlws', 'handle': 'inkpixels.bsky.social', 'display_name': 'ink', 'media_type': ['image'], 'images_cid': ['bafkreienkhaa7gtudrria37tznq4bvwtnwmuavtizqoqlq5dxesbo4yhei'], 'mime_type': 'image/jpeg'}] 
            },
            "deleted": {
                "return": [],
                "expected": []
            }
        }

    @pytest.fixture(scope="class")
    def successful_response(self, api_response):
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response, \
            patch("mdfb.core.fetch_post_details._merge_uri_chunk_to_records") as mock_merged:
            mock_response = Mock()
            mock_response.model_dump_json.return_value = json.dumps(api_response["success"]["return"])
            mock_merged.return_value = api_response["success"]["return"]
            mock_api_response.return_value = mock_response
            yield mock_api_response, api_response["success"]["expected"]

    @pytest.fixture(scope="class")
    def deleted_response(self, api_response):
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response, \
            patch("mdfb.core.fetch_post_details._merge_uri_chunk_to_records") as mock_merged:
            mock_response = Mock()
            mock_response.model_dump_json.return_value = json.dumps(api_response["deleted"]["return"])
            mock_merged.return_value = api_response["deleted"]["return"]
            mock_api_response.return_value = mock_response
            yield mock_api_response, api_response["deleted"]["expected"]
    
    def test_fetch_post_details(self, successful_response):
        mock_uris = [{"mock": "example", "poster_post_uri": ""}]
        result = fetch_post_details.fetch_post_details(mock_uris)
        assert result == successful_response[1]
        
    def test_fetch_post_details_no_uris(self, successful_response):
        result = fetch_post_details.fetch_post_details([])
        assert result == []

    def test_fetch_post_details_deleted_post(self, deleted_response, caplog):
        with caplog.at_level(logging.INFO):
            mock_uris = [{"mock": "example", "poster_post_uri": ""}]
            result = fetch_post_details.fetch_post_details(mock_uris)
        assert result == deleted_response[1]
        assert "The post associated with this URI is missing/deleted:" in caplog.text
    
class TestGetPostDetails:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        fast_retry = retry(wait=wait_fixed(0), stop=stop_after_attempt(2))
        
        with patch('tenacity.retry', return_value=fast_retry):
            import importlib
            from mdfb.core import fetch_post_details
            
            importlib.reload(fetch_post_details)
            yield

    @pytest.fixture(scope="class")
    def api_response_retry_error(self):
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response:
            mock_api_response.side_effect = [
                AtProtocolError(),
                AtProtocolError(),
                AtProtocolError()
            ]
            yield mock_api_response

    @pytest.fixture(scope="class")
    def api_response_retry_then_succeed(self):
        success_data = ["success!"]
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response:
            mock_api_response.side_effect = [
                AtProtocolError(),
                success_data
            ]
            yield {
                'mock': mock_api_response,
                'success_data': success_data
        }  

    @pytest.fixture(scope="class")
    def api_response_retry_succeeds(self):
        success_data = ["success!"]
        with patch("atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_posts") as mock_api_response:
            mock_api_response.side_effect = [
                success_data
            ]
            yield {
                'mock': mock_api_response,
                'success_data': success_data
        }  

    def test_get_post_details_exceeds_retries(self, api_response_retry_error):
        with pytest.raises(RetryError):
            fetch_post_details._get_post_details([{"mock": "example", "poster_post_uri": ""}], Mock(), Mock())

    def test_get_post_details_with_retries_success(self, api_response_retry_succeeds):
        logger = logging.getLogger('mdfb.core.fetch_post_details')  
        mock_uris = [{"mock": "example", "poster_post_uri": ""}]
        result = fetch_post_details._get_post_details_with_retries(mock_uris, Mock(), logger)
        assert result == api_response_retry_succeeds["success_data"]

    def test_get_post_details_with_retries_failure(self, api_response_retry_error, caplog):
        logger = logging.getLogger('mdfb.core.fetch_post_details')  
        mock_uris = [{"mock": "example", "poster_post_uri": ""}]
        with caplog.at_level(logging.ERROR):
            result = fetch_post_details._get_post_details_with_retries(mock_uris, Mock(), logger)
        assert result is None
        assert f"Failure to fetch records from the URIs: {mock_uris}" in caplog.text
    
    def test_get_post_details_retires_then_succeeds(self, api_response_retry_then_succeed, caplog):
        logger = logging.getLogger('mdfb.core.fetch_post_details')  
        mock_uris = [{"mock": "example", "poster_post_uri": ""}]
        with caplog.at_level(logging.ERROR):
            result = fetch_post_details._get_post_details_with_retries(mock_uris, Mock(), logger)
        assert result == api_response_retry_then_succeed["success_data"]
        assert "Error occurred fetching records from URIs:" in caplog.text

class TestFetchPostDetailsUtils:
    def test_extract_media_image(self, mocker):
        mock_input = {'posts': [{'author': {'did': 'did:plc:z72i7hdynmk6r22z27h6tvur', 'handle': 'bsky.app', 'associated': {'chat': {'allow_incoming': 'none', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:z72i7hdynmk6r22z27h6tvur/bafkreihagr2cmvl2jt4mgx3sppwe2it3fwolkrbtjrhcnwjk4jdijhsoze@jpeg', 'created_at': '2023-04-12T04:53:57.057Z', 'display_name': 'Bluesky', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreigp3wgf36lhnb73plsy4xyfpaub5xvrntmmh4lga2z75reld3qnna', 'indexed_at': '2024-11-18T02:51:34.738Z', 'record': {'created_at': '2024-11-18T02:51:26.625Z', 'text': "me watching Bluesky's user count grow by another million in a day\n\nhello and welcome to all 19M of you! 🥳", 'embed': {'images': [{'alt': 'Kris Jenner looking at a computer', 'image': {'mime_type': 'image/jpeg', 'size': 232606, 'ref': {'link': 'bafkreiddd7cus33yyfwxcjrzk77ka3zldjzt22wbvoimduwn2viuf2qdtq'}, 'py_type': 'blob'}, 'aspect_ratio': {'height': 487, 'width': 702, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#image'}], 'py_type': 'app.bsky.embed.images'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3lb6vz4ms6c25', 'embed': {'images': [{'alt': 'Kris Jenner looking at a computer', 'fullsize': 'https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:z72i7hdynmk6r22z27h6tvur/bafkreiddd7cus33yyfwxcjrzk77ka3zldjzt22wbvoimduwn2viuf2qdtq@jpeg', 'thumb': 'https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:z72i7hdynmk6r22z27h6tvur/bafkreiddd7cus33yyfwxcjrzk77ka3zldjzt22wbvoimduwn2viuf2qdtq@jpeg', 'aspect_ratio': {'height': 487, 'width': 702, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#viewImage'}], 'py_type': 'app.bsky.embed.images#view'}, 'labels': [], 'like_count': 222800, 'quote_count': 1063, 'reply_count': 5182, 'repost_count': 11589, 'threadgate': None, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}]}
        mock_input = mock_input["posts"][0]["record"]["embed"]
        result = fetch_post_details._extract_media(mock_input)
        assert result == {'media_type': ['image'], 'images_cid': ['bafkreiddd7cus33yyfwxcjrzk77ka3zldjzt22wbvoimduwn2viuf2qdtq'], 'mime_type': 'image/jpeg'}

    def test_extract_media_video(self, mocker):
        mock_input = {'posts': [{'author': {'did': 'did:plc:z72i7hdynmk6r22z27h6tvur', 'handle': 'bsky.app', 'associated': {'chat': {'allow_incoming': 'none', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:z72i7hdynmk6r22z27h6tvur/bafkreihagr2cmvl2jt4mgx3sppwe2it3fwolkrbtjrhcnwjk4jdijhsoze@jpeg', 'created_at': '2023-04-12T04:53:57.057Z', 'display_name': 'Bluesky', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreigah7oevnzroay2ve56w7pd3atscamiekwqbmj3kl66mvqsuydtwe', 'indexed_at': '2024-11-15T00:53:48.256Z', 'record': {'created_at': '2024-11-15T00:53:46.785Z', 'text': "it's official — 1,000,000 people have joined Bluesky in just the last day!!! \n\nwelcome and thank you for being here 🥳", 'embed': {'video': {'mime_type': 'video/mp4', 'size': 1787532, 'ref': {'link': 'bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq'}, 'py_type': 'blob'}, 'alt': 'Barbie smiling, clapping, and jumping up and down', 'aspect_ratio': {'height': 640, 'width': 1280, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'captions': None, 'py_type': 'app.bsky.embed.video'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3lax5zxh7bc2p', 'embed': {'cid': 'bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq', 'playlist': 'https://video.bsky.app/watch/did%3Aplc%3Az72i7hdynmk6r22z27h6tvur/bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq/playlist.m3u8', 'alt': 'Barbie smiling, clapping, and jumping up and down', 'aspect_ratio': {'height': 640, 'width': 1280, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'thumbnail': 'https://video.bsky.app/watch/did%3Aplc%3Az72i7hdynmk6r22z27h6tvur/bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq/thumbnail.jpg', 'py_type': 'app.bsky.embed.video#view'}, 'labels': [], 'like_count': 88777, 'quote_count': 1724, 'reply_count': 2380, 'repost_count': 8951, 'threadgate': None, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}]}
        mock_input = mock_input["posts"][0]["record"]["embed"]
        result = fetch_post_details._extract_media(mock_input)
        assert result == {'media_type': ['video'], 'video_cids': 'bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq', 'mime_type': 'video/mp4'}

    def test_get_rkey(self, mocker):
        mock_input = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3lax5zxh7bc2p"
        expected = "3lax5zxh7bc2p"
        result = fetch_post_details._get_rkey(mock_input)
        assert result == expected

    def test_get_author_details(self, mocker):
        mock_input = {'posts': [{'author': {'did': 'did:plc:z72i7hdynmk6r22z27h6tvur', 'handle': 'bsky.app', 'associated': {'chat': {'allow_incoming': 'none', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:z72i7hdynmk6r22z27h6tvur/bafkreihagr2cmvl2jt4mgx3sppwe2it3fwolkrbtjrhcnwjk4jdijhsoze@jpeg', 'created_at': '2023-04-12T04:53:57.057Z', 'display_name': 'Bluesky', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreigah7oevnzroay2ve56w7pd3atscamiekwqbmj3kl66mvqsuydtwe', 'indexed_at': '2024-11-15T00:53:48.256Z', 'record': {'created_at': '2024-11-15T00:53:46.785Z', 'text': "it's official — 1,000,000 people have joined Bluesky in just the last day!!! \n\nwelcome and thank you for being here 🥳", 'embed': {'video': {'mime_type': 'video/mp4', 'size': 1787532, 'ref': {'link': 'bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq'}, 'py_type': 'blob'}, 'alt': 'Barbie smiling, clapping, and jumping up and down', 'aspect_ratio': {'height': 640, 'width': 1280, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'captions': None, 'py_type': 'app.bsky.embed.video'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3lax5zxh7bc2p', 'embed': {'cid': 'bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq', 'playlist': 'https://video.bsky.app/watch/did%3Aplc%3Az72i7hdynmk6r22z27h6tvur/bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq/playlist.m3u8', 'alt': 'Barbie smiling, clapping, and jumping up and down', 'aspect_ratio': {'height': 640, 'width': 1280, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'thumbnail': 'https://video.bsky.app/watch/did%3Aplc%3Az72i7hdynmk6r22z27h6tvur/bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq/thumbnail.jpg', 'py_type': 'app.bsky.embed.video#view'}, 'labels': [], 'like_count': 88777, 'quote_count': 1724, 'reply_count': 2380, 'repost_count': 8951, 'threadgate': None, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}]}
        mock_input = mock_input["posts"][0]["author"]
        result = fetch_post_details._get_author_details(mock_input)
        assert result == {'did': 'did:plc:z72i7hdynmk6r22z27h6tvur', 'handle': 'bsky.app', 'display_name': 'Bluesky'}

    def test_merge_uri_chunk_to_records(self, mocker):
        mock_uri_chunk = [{"poster_post_uri": "example_uri_1"}, {"poster_post_uri": "example_uri_2"}]
        mock_records = {"posts": [{"uri": "example_uri_1"}, {"uri": "example_uri_2"}]}

        result = fetch_post_details._merge_uri_chunk_to_records(mock_uri_chunk, mock_records)
        assert result == [{"uri": "example_uri_1", "poster_post_uri": "example_uri_1"}, {"uri": "example_uri_2", "poster_post_uri": "example_uri_2"}]