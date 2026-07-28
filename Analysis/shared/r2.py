"""
Lazy data access: serve files from local disk, optionally downloading from
object storage on first use.

Every script in this repository reads its inputs through ``ensure_data_file``,
which resolves a path relative to ``Analysis/Data/``. If the file is already on
disk it is returned as-is and no network access happens.

Reproducers: the licensed inputs (Revelio Labs, BoardEx, Audit Analytics) cannot
be redistributed, so place them under ``Analysis/Data/`` yourself using the
layout documented in ``Analysis/pipeline/README.md``. Scripts 01-03 in
``Analysis/pipeline/`` download them directly from WRDS if you hold the relevant
subscriptions. See ``DATA_AVAILABILITY.md`` for the full per-source rundown.

The optional S3-compatible download path exists for the authors' own archive and
is used only when all of these are set in the environment:

    R2_ACCESS_KEY_ID       access key
    R2_SECRET_ACCESS_KEY   secret key
    R2_ENDPOINT            full endpoint URL  (or R2_ACCOUNT_ID for Cloudflare R2)
    R2_BUCKET              bucket name        (default: "gender")

No credentials are embedded in this repository.

Usage:
    from shared.r2 import ensure_data_file
    path = ensure_data_file("processed/revB4AudStata.feather")
"""
import os

_R2_BUCKET = os.environ.get("R2_BUCKET", "gender")


class DataFileUnavailable(FileNotFoundError):
    """A required input is absent locally and cannot be fetched."""


def _get_endpoint():
    """Return the S3-compatible endpoint URL, or None if not configured."""
    endpoint = os.environ.get("R2_ENDPOINT")
    if endpoint:
        return endpoint
    account_id = os.environ.get("R2_ACCOUNT_ID")
    if account_id:
        return f"https://{account_id}.r2.cloudflarestorage.com"
    return None


def _get_r2_credentials():
    """Return (access_key, secret_key, endpoint), or (None, None, None) if unset.

    Reads the environment first, then Colab secrets as a convenience for
    notebook use. Never falls back to embedded credentials.
    """
    key = os.environ.get("R2_ACCESS_KEY_ID")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY")
    endpoint = _get_endpoint()
    if key and secret and endpoint:
        return key, secret, endpoint

    try:
        from google.colab import userdata  # noqa: PLC0415
        key = key or userdata.get("R2_ACCESS_KEY_ID")
        secret = secret or userdata.get("R2_SECRET_ACCESS_KEY")
        endpoint = endpoint or userdata.get("R2_ENDPOINT")
    except Exception:
        pass

    if key and secret and endpoint:
        return key, secret, endpoint
    return None, None, None


def remote_configured():
    """Return True if the optional object-storage download path is available."""
    return all(_get_r2_credentials())


def _get_s3_client():
    """Create a boto3 S3 client (cached on module). Raises if unconfigured."""
    global _s3_client
    try:
        return _s3_client
    except NameError:
        pass

    access_key, secret_key, endpoint = _get_r2_credentials()
    if not (access_key and secret_key and endpoint):
        raise DataFileUnavailable(
            "Object-storage credentials are not configured. Set "
            "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_ENDPOINT (or "
            "R2_ACCOUNT_ID) to enable downloads, or place the required input "
            "files under Analysis/Data/ by hand -- see DATA_AVAILABILITY.md."
        )

    import boto3
    _s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    return _s3_client


def ensure_data_file(subpath):
    """Return the local path to a data file, downloading it if necessary.

    Resolution order:
      1. ``Analysis/Data/<subpath>`` if it exists
      2. ``Analysis/Data/public/<subpath>`` -- the non-proprietary inputs
         committed to this repository
      3. object storage, if credentials are configured

    Args:
        subpath: Path relative to Analysis/Data/, e.g.
                 "processed/revB4AudStata.feather" or
                 "raw/audit_analytics/audit_audit_comp_feed34_revised_audit_opinions.csv"

    Returns:
        Absolute local file path.

    Raises:
        DataFileUnavailable: the file is absent and cannot be fetched. The
            message names the file so it can be matched against
            DATA_AVAILABILITY.md.
    """
    from shared.paths import data_dir

    local_path = os.path.join(data_dir, subpath)
    if os.path.exists(local_path):
        return local_path

    public_path = os.path.join(data_dir, "public", subpath)
    if os.path.exists(public_path):
        return public_path

    if not remote_configured():
        raise DataFileUnavailable(
            f"Required input not found: Analysis/Data/{subpath}\n"
            f"  Looked in: {local_path}\n"
            f"             {public_path}\n"
            "This input is not redistributable and is not committed to this "
            "repository. See DATA_AVAILABILITY.md for how to obtain it, and "
            "Analysis/pipeline/README.md for where it belongs on disk."
        )

    r2_key = f"Data/{subpath}"
    size_mb = _download(r2_key, local_path)
    print(f"  Downloaded {subpath} ({size_mb:.1f} MB)")
    return local_path


def upload_to_r2(subpath):
    """Upload a local data file to object storage (authors' archive only).

    No-op with a warning when credentials are not configured, so that pipeline
    scripts run fine for reproducers who have no archive to write to.

    Args:
        subpath: Path relative to Analysis/Data/, e.g.
                 "raw/boardex/na_wrds_org_summary.feather"
    """
    from shared.paths import data_dir

    if not remote_configured():
        print(f"  Skipping upload of {subpath} (object storage not configured)")
        return

    local_path = os.path.join(data_dir, subpath)
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")

    r2_key = f"Data/{subpath}"
    s3 = _get_s3_client()
    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    print(f"  Uploading {subpath} ({size_mb:.1f} MB)...")
    try:
        s3.upload_file(local_path, _R2_BUCKET, r2_key)
        print(f"  Uploaded {r2_key}")
    except Exception as e:
        print(f"  WARNING: upload failed ({e}), continuing...")


def _download(r2_key, local_path):
    """Download a single file from object storage. Returns size in MB."""
    s3 = _get_s3_client()

    # Get size for progress reporting
    head = s3.head_object(Bucket=_R2_BUCKET, Key=r2_key)
    size_mb = head["ContentLength"] / (1024 * 1024)

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    print(f"  Downloading {r2_key} ({size_mb:.1f} MB)...")
    s3.download_file(_R2_BUCKET, r2_key, local_path)
    return size_mb
