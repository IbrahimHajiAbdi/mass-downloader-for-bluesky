import json
import logging
import os
from unittest.mock import Mock, patch

import pytest
from atproto.exceptions import AtProtocolError

from mdfb.core import download_blobs
from mdfb.core.models import EnrichedPost
from tests.helpers import instant_retry, load_postview

FORMAT = "{RKEY}_{HANDLE}_{TEXT}"


class TestDownloadBlobsUtils:
    @pytest.fixture
    def blobs(self):
        return download_blobs.DownloadBlobs(logging.getLogger("test"), "", Mock(), FORMAT)

    def test_truncate_filename(self, blobs):
        # this filename is more than 256 bytes
        filename = "投稿（まだプロフィールではない）内の日本語テキストを検索するためにいくつかの変更を加えました。 あなたがどう思うか興味があります！\n\n[この投稿は機械翻訳を使用しました][この投稿は機械翻訳を使用しました][この投稿は機械翻訳を使用しました]"
        result = blobs._truncate_filename(filename, 256)

        def is_valid_utf8(string: str) -> bool:
            try:
                string.encode("utf-8")
                return True
            except (UnicodeEncodeError, UnicodeDecodeError):
                return False

        assert len(result.encode("utf-8")) <= 256
        assert is_valid_utf8(result)

    def test_make_base_filename(self):
        filename_options = {"RKEY": "3213213mkmlk", "TEXT": "example_filename", "HANDLE": "handle_example"}
        blobs = download_blobs.DownloadBlobs(logging.getLogger("test"), "", Mock(), "{RKEY}_{TEXT}_{HANDLE}")
        result = blobs._make_base_filename(filename_options)
        assert result == "3213213mkmlk_example_filename_handle_example"

    def test_append_extension_mime_type(self, blobs):
        result = blobs._append_extension("filename_example", mime_type="image/jpeg")
        assert result == "filename_example.jpeg"

    def test_append_extension_i(self, blobs):
        result = blobs._append_extension("filename_example", i=2)
        assert result == "filename_example_2"

    def test_append_extension_full(self, blobs):
        result = blobs._append_extension("filename_example", mime_type="image/jpeg", i=2)
        assert result == "filename_example_2.jpeg"


class TestDownloadBlobs:
    @pytest.fixture(scope="class", autouse=True)
    def mock_instant_retry(self):
        with instant_retry(download_blobs):
            yield

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return str(tmp_path)

    @pytest.fixture
    def blobs(self, temp_dir, temp_db):
        return download_blobs.DownloadBlobs(logging.getLogger("mdfb.core.download_blobs"), temp_dir, temp_db, FORMAT)

    @pytest.fixture
    def successful_get_blob(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoSyncNamespace.get_blob") as mock_download_blob:
            mock_blob_data = b"0x3eb"
            mock_download_blob.return_value = mock_blob_data
            yield {"returned": mock_download_blob, "expected": mock_blob_data}

    @pytest.fixture
    def exceed_retries_get_blob(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoSyncNamespace.get_blob") as mock_download_blob:
            mock_download_blob.side_effect = [AtProtocolError(), AtProtocolError(), AtProtocolError()]
            yield mock_download_blob

    @pytest.fixture
    def retries_then_succeeds_get_blob(self):
        with patch("atproto_client.namespaces.sync_ns.ComAtprotoSyncNamespace.get_blob") as mock_download_blob:
            mock_blob_data = b"0x3eb"
            mock_download_blob.side_effect = [AtProtocolError(), mock_blob_data]
            yield {"returned": mock_download_blob, "expected": mock_blob_data}

    @pytest.fixture
    def enriched_image_post(self):
        response = load_postview("post_image")
        return EnrichedPost(
            response=response,
            did="did:plc:3eatnvb2dim4l7fiwln5wow6",
            rkey="3lqwz2kuzg22s",
            text="",
            handle="dailybunnies.bsky.social",
            display_name="daily bunnies",
            media_type=["image"],
            images_cid=["bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze"],
            mime_type="image/jpeg",
            user_did="did:plc:u6iyyil77bqv5fknwauj3tfk",
            user_post_uri=["at://did:plc:u6iyyil77bqv5fknwauj3tfk/app.bsky.feed.repost/3lqx3fnspgj2s"],
            poster_post_uri="at://did:plc:3eatnvb2dim4l7fiwln5wow6/app.bsky.feed.post/3lqwz2kuzg22s",
            feed_type=["repost"],
        )

    def test_get_blob(self, blobs, successful_get_blob, temp_dir):
        mock_filename = "example_filename.jpg"
        blobs._get_blob("mock_did", "mock_cid", mock_filename)

        expected_file_path = os.path.join(temp_dir, mock_filename)
        assert os.path.exists(expected_file_path)
        with open(expected_file_path, "rb") as f:
            assert f.read() == successful_get_blob["expected"]

    def test_get_blob_exceed_retries(self, blobs, exceed_retries_get_blob, caplog):
        mock_did, mock_cid = "did:example:1234", "example_1234"
        with caplog.at_level(logging.ERROR), pytest.raises(Exception):
            blobs._get_blob(mock_did, mock_cid, "example_filename")

        assert exceed_retries_get_blob.call_count == 2
        assert f"Error occured for downloading this file, DID: {mock_did}, CID: {mock_cid}" in caplog.text

    def test_get_blob_retries_then_succeeds(self, blobs, retries_then_succeeds_get_blob, caplog):
        mock_did, mock_cid = "did:example:1234", "example_1234"
        with caplog.at_level(logging.ERROR):
            blobs._get_blob(mock_did, mock_cid, "example_filename")

        assert retries_then_succeeds_get_blob["returned"].call_count == 2
        assert f"Error occured for downloading this file, DID: {mock_did}, CID: {mock_cid}" in caplog.text

    def test_get_blob_with_retries_failure(self, blobs, exceed_retries_get_blob, caplog):
        mock_did, mock_cid = "did:example:1234", "example_1234"
        with caplog.at_level(logging.ERROR):
            response = blobs._get_blob_with_retries(mock_did, mock_cid, "example_filename")

        assert not response
        assert f"Error occured for downloading this file, DID: {mock_did}, CID: {mock_cid}" in caplog.text

    def test_get_blob_with_retries_success(self, blobs, successful_get_blob, temp_dir):
        response = blobs._get_blob_with_retries("did:example:1234", "example_1234", "example_filename")

        expected_file_path = os.path.join(temp_dir, "example_filename")
        assert os.path.exists(expected_file_path)
        with open(expected_file_path, "rb") as f:
            assert f.read() == successful_get_blob["expected"]
        assert response
        assert successful_get_blob["returned"].call_count == 1

    def test_download_blob(self, blobs, enriched_image_post, successful_get_blob, temp_dir):
        base_filename = "3lqwz2kuzg22s_dailybunnies.bsky.social_"
        blobs.download_blobs([enriched_image_post], Mock())

        expected_image = os.path.join(temp_dir, base_filename + ".jpeg")
        expected_json = os.path.join(temp_dir, base_filename + ".json")
        assert os.path.exists(expected_image)
        assert os.path.exists(expected_json)

        with open(expected_image, "rb") as f_jpeg:
            assert f_jpeg.read() == successful_get_blob["expected"]
        with open(expected_json) as f_json:
            assert json.load(f_json) == enriched_image_post.response.model_dump(mode="json")
