import argparse
import re
from mdfb.utils.validation import validate_did
from mdfb.core.resolve_handle import resolve_handle

def is_did(did: str) -> bool:
    """
    is_did: checks if the given did is valid

    Args:
        did (str): Did

    Returns:
        bool: Whether the did is valid
    """
    if not re.search(r"^did:[a-z]+:[a-zA-Z0-9._:%-]*[a-zA-Z0-9._-]$", did):
        return False
    return True

def account_or_did(args: argparse.Namespace, did: str) -> str:
    if args.restore:
        return args.restore
    else:
        return args.handle if args.handle else did

def get_did(args: argparse.Namespace) -> str:
    if args.restore: 
        if args.restore is True:
            did = None
        else:
            did = args.restore if is_did(args.restore) else resolve_handle(args.restore)
    else:
        did = validate_did(args.did) if args.did else resolve_handle(args.handle)
    return did