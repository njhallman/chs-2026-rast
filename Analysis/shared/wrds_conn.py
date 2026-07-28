"""
WRDS connection helper.

The download scripts (``pipeline/01``-``03``) need a WRDS account with Revelio
Labs, BoardEx, and Audit Analytics subscriptions. Supply your own username --
there is no default:

    python Analysis/pipeline/02_download_boardex.py --wrds-username YOUR_ID
    WRDS_USERNAME=YOUR_ID python Analysis/pipeline/02_download_boardex.py

Every connection triggers a Duo two-factor push. Approve it promptly; repeated
failed attempts can lock the account, so do not loop on connection errors.
"""
import argparse
import os


def add_wrds_argument(parser):
    """Add the standard --wrds-username option to an ArgumentParser."""
    parser.add_argument(
        '--wrds-username',
        default=os.environ.get('WRDS_USERNAME'),
        help='WRDS account username (default: $WRDS_USERNAME)',
    )
    return parser


def resolve_username(username=None):
    """Return the WRDS username, or exit with an actionable message."""
    username = username or os.environ.get('WRDS_USERNAME')
    if not username:
        raise SystemExit(
            "No WRDS username provided. Pass --wrds-username YOUR_ID or set "
            "WRDS_USERNAME in the environment. A WRDS subscription covering "
            "Revelio Labs, BoardEx, and Audit Analytics is required -- see "
            "DATA_AVAILABILITY.md."
        )
    return username


def connect(username=None):
    """Open a WRDS connection, prompting for Duo two-factor approval.

    Args:
        username: WRDS account name. Falls back to $WRDS_USERNAME.

    Returns:
        An open ``wrds.Connection``.
    """
    import wrds

    username = resolve_username(username)
    print("WARNING: This requires WRDS Duo 2FA. Watch for the push notification.")
    print(f"Connecting to WRDS as {username}...\n")
    return wrds.Connection(wrds_username=username)


__all__ = ['add_wrds_argument', 'resolve_username', 'connect', 'argparse']
