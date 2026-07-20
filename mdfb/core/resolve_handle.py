import logging


def resolve_handle(handle: str) -> str:
    """
    resolve_handle: for a given handle, uses atproto API: com.atproto.identity.resolveHandle, to resolve the handle to a DID

    Args:
        handle (str): handle of the target account

    Raises:
        DidNotFoundError: if the handle is able to be resolved

    Returns:
        str: resolved DID

    """
    from atproto_identity.exceptions import DidNotFoundError
    from atproto_identity.handle.resolver import HandleResolver

    logger = logging.getLogger(__name__)
    try:
        did = HandleResolver().ensure_resolve(handle)
    except DidNotFoundError:
        logger.error(f"Unable to resolve handle: {handle}")
        raise DidNotFoundError(f"Unable to resolve handle: {handle}")
    return did
