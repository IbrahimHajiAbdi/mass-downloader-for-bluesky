import os
import json
import logging
import tempfile
import pytest
from unittest.mock import patch
from tenacity import stop_after_attempt, retry, wait_fixed
from atproto.exceptions import AtProtocolError
from mdfb.core import download_blobs 

class TestDownloadBlobsUtils:
    def test_truncate_filename(self):
        # this filename is more than 256 bytes
        filename = "投稿（まだプロフィールではない）内の日本語テキストを検索するためにいくつかの変更を加えました。 あなたがどう思うか興味があります！\n\n[この投稿は機械翻訳を使用しました][この投稿は機械翻訳を使用しました][この投稿は機械翻訳を使用しました]"
        result = download_blobs._truncate_filename(filename, 256)
        def is_valid_utf8(string: str) -> bool:
            try:
                string.encode('utf-8')
                return True
            except (UnicodeEncodeError, UnicodeDecodeError):
                return False
            
        assert len(result.encode("utf-8")) <= 256 
        assert is_valid_utf8(result)

    def test_make_base_filename(self):
        filename_options = {
            "RKEY": "3213213mkmlk",
            "TEXT": "example_filename",
            "HANDLE": "handle_example"
        }
        filename_format_string = "{RKEY}_{TEXT}_{HANDLE}"
        result = download_blobs._make_base_filename(filename_options, filename_format_string)
        assert result == f"{filename_options.get('RKEY')}_{filename_options.get('TEXT')}_{filename_options.get('HANDLE')}"

    def test_append_extension_mime_type(self):
        mime_type = "image/jpeg"
        file_type = "jpeg"
        filename = "filename_example"
        result = download_blobs._append_extension(filename, mime_type=mime_type)
        assert result == f"{filename}.{file_type}"

    def test_append_extension_i(self):
        i = 2
        filename = "filename_example"
        result = download_blobs._append_extension(filename, i=2) 
        assert result == f"{filename}_{i}"

    def test_append_extension_full(self):
        mime_type = "image/jpeg"
        file_type = "jpeg"
        i = 2
        filename = "filename_example"
        result = download_blobs._append_extension(filename, mime_type=mime_type, i=i)
        assert result == f"{filename}_{i}.{file_type}"

class TestDownloadBlobs:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        fast_retry = retry(wait=wait_fixed(0), stop=stop_after_attempt(2))
        
        with patch('tenacity.retry', return_value=fast_retry):
            import importlib
            from mdfb.core import download_blobs
            
            importlib.reload(download_blobs)
            yield

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture(scope="function")
    def successful_get_blob(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoSyncNamespace.get_blob") as mock_download_blob: 
            mock_blob_data = b"0x3eb"   
            mock_download_blob.return_value = mock_blob_data
            yield {
                "returned": mock_download_blob,
                "expected": mock_blob_data
            }

    @pytest.fixture(scope="function")
    def exceed_retries_get_blob(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoSyncNamespace.get_blob") as mock_download_blob: 
            mock_download_blob.side_effect = [
                AtProtocolError(),
                AtProtocolError(),
                AtProtocolError()
            ]
            yield mock_download_blob

    @pytest.fixture(scope="function")
    def retries_then_succeeds_get_blob(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoSyncNamespace.get_blob") as mock_download_blob: 
            mock_blob_data = b"0x3eb"   
            mock_download_blob.side_effect = [
                AtProtocolError(),
                mock_blob_data
            ]
            yield {
                "returned": mock_download_blob,
                "expected": mock_blob_data
            }   

    @pytest.fixture(scope="function")
    def successful_download_blobs(self):
        mock_post = [{'rkey': '3lqwz2kuzg22s', 'text': '', 'response': {'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.repost/3lqx3fnspgj2s'], 'feed_type': ['repost'], 'poster_post_uri': 'at://did:plc:3eatnvb2dim4l7fiwln5wow6/app.bsky.feed.post/3lqwz2kuzg22s', 'author': {'did': 'did:plc:3eatnvb2dim4l7fiwln5wow6', 'handle': 'dailybunnies.bsky.social', 'associated': {'chat': {'allow_incoming': 'none', 'py_type': 'app.bsky.actor.defs#profileAssociatedChat'}, 'feedgens': None, 'labeler': None, 'lists': None, 'starter_packs': None, 'py_type': 'app.bsky.actor.defs#profileAssociated'}, 'avatar': 'https://cdn.bsky.app/img/avatar/plain/did:plc:3eatnvb2dim4l7fiwln5wow6/bafkreifz2jzlibiyldp75uhdi4xhlpww6khmkt5brpj2jif274kocrv3xq@jpeg', 'created_at': '2024-10-20T14:50:10.507Z', 'display_name': 'daily bunnies 🐇✨', 'labels': [], 'viewer': None, 'py_type': 'app.bsky.actor.defs#profileViewBasic'}, 'cid': 'bafyreib3qtxun7gvvpjaxk666xxvkltu2oyyghekziswhwtmutz6xz2vh4', 'indexed_at': '2025-06-06T14:07:49.256Z', 'record': {'created_at': '2025-06-06T14:07:44.486Z', 'text': '', 'embed': {'images': [{'alt': 'A small, white bunny stands on its hind legs, peering out a window. Lush green trees are visible outside.', 'image': {'mime_type': 'image/jpeg', 'size': 659942, 'ref': {'link': 'bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze'}, 'py_type': 'blob'}, 'aspect_ratio': {'height': 1440, 'width': 1080, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#image'}], 'py_type': 'app.bsky.embed.images'}, 'entities': None, 'facets': None, 'labels': None, 'langs': ['en'], 'reply': None, 'tags': None, 'py_type': 'app.bsky.feed.post'}, 'uri': 'at://did:plc:3eatnvb2dim4l7fiwln5wow6/app.bsky.feed.post/3lqwz2kuzg22s', 'embed': {'images': [{'alt': 'A small, white bunny stands on its hind legs, peering out a window. Lush green trees are visible outside.', 'fullsize': 'https://cdn.bsky.app/img/feed_fullsize/plain/did:plc:3eatnvb2dim4l7fiwln5wow6/bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze@jpeg', 'thumb': 'https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:3eatnvb2dim4l7fiwln5wow6/bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze@jpeg', 'aspect_ratio': {'height': 1440, 'width': 1080, 'py_type': 'app.bsky.embed.defs#aspectRatio'}, 'py_type': 'app.bsky.embed.images#viewImage'}], 'py_type': 'app.bsky.embed.images#view'}, 'labels': [], 'like_count': 4187, 'quote_count': 35, 'reply_count': 68, 'repost_count': 386, 'threadgate': None, 'viewer': None, 'py_type': 'app.bsky.feed.defs#postView'}, 'user_did': 'did:plc:u6iyyil77bqv5fknwauj3tfk', 'user_post_uri': ['at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.repost/3lqx3fnspgj2s'], 'poster_post_uri': 'at://did:plc:3eatnvb2dim4l7fiwln5wow6/app.bsky.feed.post/3lqwz2kuzg22s', 'feed_type': ['repost'], 'did': 'did:plc:3eatnvb2dim4l7fiwln5wow6', 'handle': 'dailybunnies.bsky.social', 'display_name': 'daily bunnies 🐇✨', 'media_type': ['image'], 'images_cid': ['bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze'], 'mime_type': 'image/jpeg'}]
        post_response = mock_post[0]["response"]
        mock_base_filename = "3lqwz2kuzg22s_dailybunnies.bsky.social_"
        with patch("tqdm.tqdm") as mock_tdqm, \
        patch("mdfb.utils.database.insert_post"):
            yield {
                "post": mock_post,
                "post_response": post_response,
                "filename": mock_base_filename,
                "mock_tdqm": mock_tdqm
            }

    def test_get_blob(self, successful_get_blob, temp_dir):
        mock_filename = "example_filename.jpg"
        logger = logging.getLogger('mdfb.core.download_blobs')
        
        download_blobs._get_blob("mock_did", "mock_cid", mock_filename, temp_dir, logger)
        
        expected_file_path = os.path.join(temp_dir, mock_filename)
        assert os.path.exists(expected_file_path), f"File {expected_file_path} was not created"
        
        with open(expected_file_path, "rb") as f:
            actual_data = f.read()
        
        assert actual_data == successful_get_blob["expected"], \
            f"File contents don't match. Expected: {successful_get_blob.get('expected')}, Got: {actual_data}"
        
    def test_get_blob_exceed_retries(self, exceed_retries_get_blob, caplog, temp_dir):
        mock_did = "did:example:1234"
        mock_cid = "example_1234"
        mock_filename = "example_filename"
        logger = logging.getLogger('mdfb.core.download_blobs')

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception):
                download_blobs._get_blob(mock_did, mock_cid, mock_filename, temp_dir, logger)
        
        assert exceed_retries_get_blob.call_count == 2
        assert f"Error occured for downloading this file, DID: {mock_did}, CID: {mock_cid}" in caplog.text
        
        
    def test_get_blob_retries_the_succeeds(self, retries_then_succeeds_get_blob, caplog, temp_dir):
        mock_did = "did:example:1234"
        mock_cid = "example_1234"
        mock_filename = "example_filename"
        logger = logging.getLogger('mdfb.core.download_blobs')
        
        with caplog.at_level(logging.ERROR):
            download_blobs._get_blob(mock_did, mock_cid, mock_filename, temp_dir, logger)
        
        assert retries_then_succeeds_get_blob["returned"].call_count == 2
        assert f"Error occured for downloading this file, DID: {mock_did}, CID: {mock_cid}" in caplog.text

    def test_get_blob_with_retries_failure(self, exceed_retries_get_blob, caplog, temp_dir):
        mock_did = "did:example:1234"
        mock_cid = "example_1234"
        mock_filename = "example_filename"
        logger = logging.getLogger('mdfb.core.download_blobs')

        with caplog.at_level(logging.ERROR):
            response = download_blobs._get_blob_with_retries(mock_did, mock_cid, mock_filename, temp_dir, logger)
        
        assert not response
        assert f"Error occured for downloading this file, DID: {mock_did}, CID: {mock_cid}" in caplog.text

    def test_get_blob_with_retries_success(self, successful_get_blob, caplog, temp_dir):
        mock_did = "did:example:1234"
        mock_cid = "example_1234"
        mock_filename = "example_filename"
        logger = logging.getLogger('mdfb.core.download_blobs')
        
        response = download_blobs._get_blob_with_retries(mock_did, mock_cid, mock_filename, temp_dir, logger)
        
        expected_file_path = os.path.join(temp_dir, mock_filename)
        assert os.path.exists(expected_file_path), f"File {expected_file_path} was not created"
        
        with open(expected_file_path, "rb") as f:
            actual_data = f.read()
        
        assert response
        assert actual_data == successful_get_blob["expected"]
        assert successful_get_blob["returned"].call_count == 1

    def test_download_blob(self, successful_download_blobs, temp_dir, successful_get_blob):
        download_blobs.download_blobs(successful_download_blobs["post"], temp_dir, successful_download_blobs["mock_tdqm"])
        
        expected_file_path_image = os.path.join(temp_dir, successful_download_blobs["filename"] + ".jpeg")
        expected_file_path_json = os.path.join(temp_dir, successful_download_blobs["filename"] + ".json")
        assert os.path.exists(expected_file_path_image), f"File {expected_file_path_image} was not created"
        assert os.path.exists(expected_file_path_json), f"File {expected_file_path_json} was not created"
        
        with open(expected_file_path_image, "rb") as f_jpeg:
            actual_data_jpeg = f_jpeg.read()
        assert actual_data_jpeg == successful_get_blob["expected"]

        with open(expected_file_path_json, "r") as f_json:
            actual_data_json = json.load(f_json)
        assert actual_data_json == successful_download_blobs["post_response"]