import argparse
import logging
import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch

import platformdirs
import pytest

from mdfb.utils import database, validation


@pytest.fixture(scope="function")
def temp_db_path():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def setup_test_db(temp_db_path):
    database.create_db(temp_db_path)

    con = sqlite3.connect(os.path.join(temp_db_path, "mdfb.db"))
    cur = con.cursor()

    test_data = [
        ("user1", "post1", "feed1", "poster1"),
    ]

    cur.executemany(
        """
        INSERT INTO downloaded_posts (user_did, user_post_uri, feed_type, poster_post_uri)
        VALUES (?, ?, ?, ?)
    """,
        test_data,
    )

    con.commit()
    con.close()

    return temp_db_path


@pytest.fixture(scope="function")
def mock_connect_db(setup_test_db):
    def mock_connect():
        return sqlite3.connect(os.path.join(setup_test_db, "mdfb.db"))

    with patch.object(database, "connect_db", side_effect=mock_connect):
        yield


class TestValidateLimit:
    @pytest.mark.parametrize("input_val,expected", [("10", 10)])
    def test_validate_limit(self, input_val, expected):
        result = validation.validate_limit(input_val)
        assert result == expected

    @pytest.mark.parametrize("invalid_input", ["-1", "0"])
    def test_validate_limit_under_1(self, invalid_input):
        with pytest.raises(ValueError):
            validation.validate_limit(invalid_input)

    @pytest.mark.parametrize("invalid_input", ["a"])
    def test_validate_limit_not_number(self, invalid_input):
        with pytest.raises(ValueError):
            validation.validate_limit(invalid_input)


class TestValidateDirectory:
    def test_validate_directory(self):
        with tempfile.TemporaryDirectory() as mock_dir:
            mock_parser = argparse.ArgumentParser()
            result = validation.validate_directory(mock_dir, mock_parser)
            assert result == mock_dir

    def test_validate_directory_bad_path(self):
        mock_dir = "bad_path"
        mock_parser = argparse.ArgumentParser()
        with pytest.raises(ValueError):
            validation.validate_directory(mock_dir, mock_parser)

    def test_validate_directory_nonexistant_path(self, capsys):
        mock_dir = ""
        mock_parser = argparse.ArgumentParser()
        with pytest.raises(SystemExit):
            validation.validate_directory(mock_dir, mock_parser)
        captured = capsys.readouterr()
        assert "Please enter a directory as a positional argument" in captured.err


class TestvalidateDid:
    def test_validate_did(self):
        mock_did = "did:plc:123abc"
        result = validation.validate_did(mock_did)
        assert result == mock_did

    @pytest.mark.parametrize("invalid_input", ["dnsadnasndjkl", ""])
    def test_validate_did_invalid(self, invalid_input):
        with pytest.raises(ValueError):
            validation.validate_did(invalid_input)


class TestValidateThreads:
    def test_validate_threads(self):
        mock_threads = "1"
        result = validation.validate_threads(mock_threads)
        assert result == 1

    def test_validate_threads_invalid(self):
        mock_threads = "a"
        with pytest.raises(ValueError):
            validation.validate_threads(mock_threads)

    def test_validate_threads_too_big(self, monkeypatch):
        mock_threads = "10"
        max_threads = 3
        monkeypatch.setattr("mdfb.utils.validation.MAX_THREADS", max_threads)

        result = validation.validate_threads(mock_threads)
        assert result == max_threads

    def test_validate_threads_too_little(self):
        mock_threads = "0"
        with pytest.raises(ValueError):
            validation.validate_threads(mock_threads)


class TestValidateFormat:
    @pytest.mark.parametrize("input_val", ["{RKEY}_{DID}", "{TEXT}_{HANDLE}"])
    def test_validate_format_true(self, input_val):
        result = validation.validate_format(input_val)
        assert result == input_val

    @pytest.mark.parametrize("invalid_input", ["{JOHN}_{DID}", "{DID}_{ALLY}"])
    def test_validate_format_invalid_input(self, invalid_input):
        with pytest.raises(ValueError):
            validation.validate_format(invalid_input)


class TestValidateNoPosts:
    @pytest.mark.parametrize(
        "input_values",
        [
            ([1], "example account", ["like"], False, "", True),
            ([1], "example account", ["like"], False, "user1", True),
            ([1], "example account", ["like"], False, "", False),
            ([1], "example account", ["like"], True, "", False),
        ],
    )
    def test_validate_no_posts(self, mock_connect_db, input_values):
        validation.validate_no_posts(*input_values)

    @pytest.mark.parametrize(
        "invalid_inputs",
        [
            ([], "example account", ["like"], False, "", True),
            ([1], "example account", ["like"], False, "user2", True),
            ([], "example account", ["like"], False, "user2", False),
            ([], "example account", ["like"], True, "user2", False),
        ],
    )
    def test_validate_no_posts_errors(self, mock_connect_db, invalid_inputs):
        with pytest.raises(ValueError):
            validation.validate_no_posts(*invalid_inputs)


class TestValidateDatabase:
    def test_validate_database_false_dir(self, caplog, mock_connect_db):
        with caplog.at_level(logging.INFO), tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(platformdirs, "user_data_path") as mock_user_data_path,
                patch.object(platformdirs, "user_data_dir") as mock_user_data_dir,
            ):
                mock_user_data_path.return_value = "false_dir"
                mock_user_data_dir.return_value = temp_dir
                validation.validate_database()
        assert "Creating database as the mdfb directory does not exist..." in caplog.text

    def test_validate_database_no_database(self, caplog, mock_connect_db):
        with caplog.at_level(logging.INFO), tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(platformdirs, "user_data_path") as mock_user_data_path,
                patch.object(platformdirs, "user_data_dir") as mock_user_data_dir,
            ):
                mock_user_data_path.return_value = temp_dir
                mock_user_data_dir.return_value = temp_dir
                validation.validate_database()
        assert "Creating database as the mdfb directory does exist, but there is no database..." in caplog.text

    def test_validate_database(self, caplog, setup_test_db):
        with (
            caplog.at_level(logging.INFO),
            patch.object(platformdirs, "user_data_path") as mock_user_data_path,
            patch.object(platformdirs, "user_data_dir") as mock_user_data_dir,
        ):
            mock_user_data_path.return_value = setup_test_db
            mock_user_data_dir.return_value = setup_test_db
            validation.validate_database()
        assert not caplog.text


class TestValidateDownload:
    def test_validate_post_types_success(self):
        mock_parser = Mock()
        args = Mock(like=True, post=False, repost=False)

        validation._validate_post_types(args, mock_parser)
        mock_parser.error.assert_not_called()

    def test_validate_post_types_error(self):
        mock_parser = Mock()
        args = Mock(like=False, post=False, repost=False)

        validation._validate_post_types(args, mock_parser)
        mock_parser.error.assert_called_once()
