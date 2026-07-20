import contextlib
import importlib
import json
from pathlib import Path
from unittest.mock import patch

from atproto_client.models.app.bsky.feed.defs import PostView
from tenacity import retry, stop_after_attempt, wait_fixed

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture_json(name: str) -> dict:
    """Load a captured API payload from tests/fixtures/<name>.json."""
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


def load_postview(name: str) -> PostView:
    """Load a fixture and validate it into a real atproto PostView."""
    return PostView.model_validate(load_fixture_json(name))


@contextlib.contextmanager
def instant_retry(module):
    """
    Reload ``module`` with tenacity's exponential backoff swapped for an
    instant, 2-attempt retry so retry-path tests run fast. Restores the module
    on exit to avoid leaking the fast retry into other test files.
    """
    fast_retry = retry(wait=wait_fixed(0), stop=stop_after_attempt(2))
    try:
        with patch("tenacity.retry", return_value=fast_retry):
            importlib.reload(module)
            yield module
    finally:
        importlib.reload(module)
