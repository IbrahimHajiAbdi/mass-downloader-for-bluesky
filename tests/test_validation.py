import argparse
import tempfile
from unittest.mock import Mock

import pytest

from mdfb.utils import validation


@pytest.fixture
def db_with_user1(temp_db, seed_rows):
    """Keeps the platformdirs patch active (so Database() in validate_no_posts hits the temp db) and seeds user1."""
    seed_rows(temp_db, [("user1", "post1", "feed1", "poster1")])
    return temp_db


class TestValidateLimit:
    @pytest.mark.parametrize("input_val,expected", [("10", 10)])
    def test_validate_limit(self, input_val, expected):
        assert validation.validate_limit(input_val) == expected

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
            assert validation.validate_directory(mock_dir, mock_parser) == mock_dir

    def test_validate_directory_bad_path(self):
        mock_parser = argparse.ArgumentParser()
        with pytest.raises(ValueError):
            validation.validate_directory("bad_path", mock_parser)

    def test_validate_directory_nonexistant_path(self, capsys):
        mock_parser = argparse.ArgumentParser()
        with pytest.raises(SystemExit):
            validation.validate_directory("", mock_parser)
        assert "Please enter a directory as a positional argument" in capsys.readouterr().err


class TestvalidateDid:
    def test_validate_did(self):
        mock_did = "did:plc:123abc"
        assert validation.validate_did(mock_did) == mock_did

    @pytest.mark.parametrize("invalid_input", ["dnsadnasndjkl", ""])
    def test_validate_did_invalid(self, invalid_input):
        with pytest.raises(ValueError):
            validation.validate_did(invalid_input)


class TestValidateThreads:
    def test_validate_threads(self):
        assert validation.validate_threads("1") == 1

    def test_validate_threads_invalid(self):
        with pytest.raises(ValueError):
            validation.validate_threads("a")

    def test_validate_threads_too_big(self, monkeypatch):
        max_threads = 3
        monkeypatch.setattr("mdfb.utils.validation.MAX_THREADS", max_threads)
        assert validation.validate_threads("10") == max_threads

    def test_validate_threads_too_little(self):
        with pytest.raises(ValueError):
            validation.validate_threads("0")


class TestValidateFormat:
    @pytest.mark.parametrize("input_val", ["{RKEY}_{DID}", "{TEXT}_{HANDLE}"])
    def test_validate_format_true(self, input_val):
        assert validation.validate_format(input_val) == input_val

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
    def test_validate_no_posts(self, db_with_user1, input_values):
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
    def test_validate_no_posts_errors(self, db_with_user1, invalid_inputs):
        with pytest.raises(ValueError):
            validation.validate_no_posts(*invalid_inputs)


class TestValidateDownload:
    def test_validate_post_types_success(self):
        mock_parser = Mock()
        args = Mock(like=True, post=False, repost=False, bookmark=False)

        validation._validate_post_types(args, mock_parser)
        mock_parser.error.assert_not_called()

    def test_validate_post_types_error(self):
        mock_parser = Mock()
        args = Mock(like=False, post=False, repost=False, bookmark=False)

        validation._validate_post_types(args, mock_parser)
        mock_parser.error.assert_called_once()
