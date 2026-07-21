import os

import pytest

SEED_DATA = [
    ("user1", "post1", "feed1", "poster1"),
    ("user1", "post2", "feed1", "poster2"),
    ("user2", "post3", "feed2", "poster3"),
    ("user2", "post4", "feed2", "poster4"),
    ("user3", "post5", "feed1", "poster5"),
]


@pytest.fixture
def seeded_db(temp_db, seed_rows):
    seed_rows(temp_db, SEED_DATA)
    return temp_db


class TestDatabase:
    def test_ensure_database_exists(self, temp_db):
        db_file = os.path.join(temp_db.db_path, "mdfb.db")
        assert os.path.exists(db_file)

        res = temp_db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downloaded_posts'")
        assert res.fetchone() is not None

    def test_empty_database_operations(self, temp_db):
        assert temp_db.check_user_exists("any_user") is False
        assert temp_db.check_post_exists("any", "any", "any") is False
        assert temp_db.check_user_has_posts("any", "any") is False
        assert temp_db.restore_posts("", {}) == []

    def test_insert_post_new_posts(self, seeded_db):
        new_posts = [
            ("user4", "post6", "feed1", "poster6"),
            ("user4", "post7", "feed2", "poster7"),
        ]
        assert seeded_db.insert_post(new_posts) is True

    def test_insert_post_duplicate_posts(self, seeded_db):
        assert seeded_db.insert_post([("user1", "post1", "feed1", "poster1")]) is False

    def test_check_post_exists_true(self, seeded_db):
        assert seeded_db.check_post_exists("user1", "post1", "feed1") is True

    def test_check_post_exists_false(self, seeded_db):
        assert seeded_db.check_post_exists("nonexistent", "post999", "feed999") is False

    def test_check_user_has_posts_true(self, seeded_db):
        assert seeded_db.check_user_has_posts("user1", "feed1") is True

    def test_check_user_has_posts_false(self, seeded_db):
        assert seeded_db.check_user_has_posts("user1", "nonexistent_feed") is False

    def test_check_user_exists_true(self, seeded_db):
        assert seeded_db.check_user_exists("user1") is True

    def test_check_user_exists_false(self, seeded_db):
        assert seeded_db.check_user_exists("nonexistent_user") is False

    def test_restore_posts_by_user(self, seeded_db):
        result = seeded_db.restore_posts("user1", {"feed1": True})
        assert len(result) == 2
        assert all(post["user_did"] == "user1" for post in result)

    def test_restore_posts_wraps_uri_and_feed_type_in_lists(self, seeded_db):
        result = seeded_db.restore_posts("user1", {"feed1": True})
        assert result[0]["user_post_uri"] == ["post1"]
        assert result[0]["feed_type"] == ["feed1"]

    def test_restore_posts_by_feed_type(self, seeded_db):
        result = seeded_db.restore_posts("", {"feed1": True, "feed2": False})
        feed1_posts = [post for post in result if "feed1" in post["feed_type"]]
        assert len(feed1_posts) == 3

    def test_restore_posts_by_user_and_feed_type(self, seeded_db):
        result = seeded_db.restore_posts("user1", {"feed1": True, "feed2": False})
        assert len(result) == 2
        assert all(post["user_did"] == "user1" for post in result)
        assert all("feed1" in post["feed_type"] for post in result)

    def test_restore_posts_all(self, seeded_db):
        assert len(seeded_db.restore_posts("", {})) == 5

    def test_restore_posts_no_matching_criteria(self, seeded_db):
        result = seeded_db.restore_posts("nonexistent_user", {"nonexistent_feed": True})
        assert result == []

    def test_delete_user_existing(self, seeded_db, capsys):
        seeded_db.delete_user("user1")
        assert seeded_db.check_user_exists("user1") is False
        assert "Deleted" in capsys.readouterr().out

    def test_delete_user_nonexistent(self, seeded_db, capsys):
        seeded_db.delete_user("nonexistent_user")
        assert "No matching rows found" in capsys.readouterr().out
