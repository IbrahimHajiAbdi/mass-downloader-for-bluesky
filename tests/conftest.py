from unittest.mock import patch

import pytest

from mdfb.utils.database import Database
from tests.helpers import load_postview


@pytest.fixture
def temp_db(tmp_path):
    """
    A Database backed by a throwaway directory. Patches platformdirs (used in
    mdfb.utils.database) so Database() — including the instance created inside
    validation.validate_no_posts — resolves to the temp location.
    """
    path = str(tmp_path)
    with (
        patch("platformdirs.user_data_dir", return_value=path),
        patch("platformdirs.user_data_path", return_value=path),
    ):
        yield Database()


@pytest.fixture
def seed_rows():
    """Helper to insert (user_did, user_post_uri, feed_type, poster_post_uri) rows into a Database."""

    def _seed(db: Database, rows: list[tuple]):
        db.connection.executemany(
            "INSERT INTO downloaded_posts (user_did, user_post_uri, feed_type, poster_post_uri) VALUES (?, ?, ?, ?)",
            rows,
        )
        db.connection.commit()

    return _seed


@pytest.fixture
def postview_loader():
    """Fixture wrapper around load_postview for tests that build real PostView objects."""
    return load_postview
