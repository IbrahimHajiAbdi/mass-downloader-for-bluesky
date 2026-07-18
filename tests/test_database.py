import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from mdfb.utils import database


class TestDatabase:
    @pytest.fixture(scope="function")
    def temp_db_path(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir

        import shutil

        shutil.rmtree(temp_dir)

    @pytest.fixture(scope="function")
    def setup_test_db(self, temp_db_path):
        database.create_db(temp_db_path)

        con = sqlite3.connect(os.path.join(temp_db_path, "mdfb.db"))
        cur = con.cursor()

        test_data = [
            ("user1", "post1", "feed1", "poster1"),
            ("user1", "post2", "feed1", "poster2"),
            ("user2", "post3", "feed2", "poster3"),
            ("user2", "post4", "feed2", "poster4"),
            ("user3", "post5", "feed1", "poster5"),
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

    @pytest.fixture(autouse=True)
    def mock_connect_db(self, setup_test_db):
        def mock_connect():
            return sqlite3.connect(os.path.join(setup_test_db, "mdfb.db"))

        with patch.object(database, "connect_db", side_effect=mock_connect):
            yield

    def test_empty_database_operations(self, temp_db_path):
        database.create_db(temp_db_path)

        with patch.object(database, "connect_db") as mock_connect:
            mock_connect.return_value = sqlite3.connect(os.path.join(temp_db_path, "mdfb.db"))

            con = database.connect_db()
            cur = con.cursor()

            cur.execute("DELETE FROM downloaded_posts;")

            assert database.check_user_exists("any_user") is False

            assert database.check_post_exists(cur, "any", "any", "any") is False
            assert database.check_user_has_posts(cur, "any", "any") is False

            result = database.restore_posts("", {})
            assert len(result) == 0

    def test_create_db(self, temp_db_path):
        new_temp_dir = tempfile.mkdtemp()
        database.create_db(new_temp_dir)

        db_path = os.path.join(new_temp_dir, "mdfb.db")
        assert os.path.exists(db_path)

        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downloaded_posts'")
        result = cur.fetchone()
        assert result is not None
        con.close()

        import shutil

        shutil.rmtree(new_temp_dir)

    def test_insert_post_new_posts(self, setup_test_db):
        con = database.connect_db()
        cur = con.cursor()

        new_posts = [
            ("user4", "post6", "feed1", "poster6"),
            ("user4", "post7", "feed2", "poster7"),
        ]

        result = database.insert_post(cur, new_posts)
        con.commit()
        con.close()

        assert result is True

    def test_insert_post_duplicate_posts(self, setup_test_db):
        con = database.connect_db()
        cur = con.cursor()

        duplicate_posts = [
            ("user1", "post1", "feed1", "poster1"),
        ]

        result = database.insert_post(cur, duplicate_posts)
        con.commit()
        con.close()

        assert result is False

    def test_check_post_exists_true(self, setup_test_db):
        con = database.connect_db()
        cur = con.cursor()

        result = database.check_post_exists(cur, "user1", "post1", "feed1")
        con.close()

        assert result is True

    def test_check_post_exists_false(self, setup_test_db):
        con = database.connect_db()
        cur = con.cursor()

        result = database.check_post_exists(cur, "nonexistent", "post999", "feed999")
        con.close()

        assert result is False

    def test_check_user_has_posts_true(self, setup_test_db):
        con = database.connect_db()
        cur = con.cursor()

        result = database.check_user_has_posts(cur, "user1", "feed1")
        con.close()

        assert result is True

    def test_check_user_has_posts_false(self, setup_test_db):
        con = database.connect_db()
        cur = con.cursor()

        result = database.check_user_has_posts(cur, "user1", "nonexistent_feed")
        con.close()

        assert result is False

    def test_check_user_exists_true(self, setup_test_db):
        result = database.check_user_exists("user1")
        assert result is True

    def test_check_user_exists_false(self, setup_test_db):
        result = database.check_user_exists("nonexistent_user")
        assert result is False

    def test_restore_posts_by_user(self, setup_test_db):
        result = database.restore_posts("user1", {"feed1": True})

        assert len(result) == 2
        assert all(post["user_did"] == "user1" for post in result)

    def test_restore_posts_by_feed_type(self, setup_test_db):
        post_types = {"feed1": True, "feed2": False}
        result = database.restore_posts("", post_types)

        feed1_posts = [post for post in result if "feed1" in post["feed_type"]]
        assert len(feed1_posts) == 3

    def test_restore_posts_by_user_and_feed_type(self, setup_test_db):
        post_types = {"feed1": True, "feed2": False}
        result = database.restore_posts("user1", post_types)

        assert len(result) == 2
        assert all(post["user_did"] == "user1" for post in result)
        assert all("feed1" in post["feed_type"] for post in result)

    def test_restore_posts_all(self, setup_test_db):
        result = database.restore_posts("", {})

        assert len(result) == 5

    def test_restore_posts_no_matching_criteria(self, setup_test_db):
        post_types = {"nonexistent_feed": True}
        result = database.restore_posts("nonexistent_user", post_types)

        assert len(result) == 0

    def test_dict_factory(self, setup_test_db):
        con = database.connect_db()
        con.row_factory = database._dict_factory
        cur = con.cursor()

        cur.execute("SELECT * FROM downloaded_posts LIMIT 1")
        row = cur.fetchone()
        con.close()

        assert isinstance(row, dict)
        assert "user_did" in row
        assert "user_post_uri" in row
        assert "feed_type" in row
        assert "poster_post_uri" in row

    def test_database_connection_error_handling(self, temp_db_path):
        with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(sqlite3.Error):
                database.connect_db()

    def test_delete_user_existing(self, setup_test_db, capsys):
        database.delete_user("user1")

        result = database.check_user_exists("user1")
        assert result is False

        captured = capsys.readouterr()
        assert "Deleted" in captured.out

    def test_delete_user_nonexistent(self, setup_test_db, capsys):
        database.delete_user("nonexistent_user")

        captured = capsys.readouterr()
        assert "No matching rows found" in captured.out
