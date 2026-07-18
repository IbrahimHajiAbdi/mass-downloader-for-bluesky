import pytest
from atproto_identity.exceptions import DidNotFoundError

from mdfb.core.resolve_handle import resolve_handle


def test_resolve_handle(mocker):
    mocked_did = "did:plc:123abc"
    mocked_handle = "example_handle"
    mocker.patch("atproto_identity.handle.resolver.HandleResolver.ensure_resolve", return_value=mocked_did)
    result = resolve_handle(mocked_handle)
    assert result == mocked_did


def test_resolve_handle_not_found(mocker):
    mocked_response = mocker.patch("atproto_identity.handle.resolver.HandleResolver.ensure_resolve")
    mocked_response.side_effect = DidNotFoundError
    with pytest.raises(DidNotFoundError):
        resolve_handle("")
