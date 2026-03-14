from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from typing import Iterator, Optional

import boto3


class S3Bucket:
    """Runtime accessor for a provisioned S3 bucket.

    Instantiated by generated SDK code — do not construct manually in most
    cases; use the generated module-level instance instead::

        import infra
        with infra.acme.storage.uploads.open("report.pdf") as f:
            data = f.read()
    """

    def __init__(
        self,
        resource_name: str,
        region: str,
        profile: Optional[str] = None,
    ) -> None:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self._client = session.client("s3", region_name=region)
        self._bucket = resource_name

    def upload(self, key: str, file_path: str, content_type: str) -> None:
        """Upload a local file to the bucket under ``key``."""
        with open(file_path, "rb") as f:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=f.read(),
                ContentType=content_type,
            )

    def delete(self, key: str) -> None:
        """Delete an object from the bucket."""
        self._client.delete_object(Bucket=self._bucket, Key=key)

    @contextmanager
    def fetch(self, key: str, temp_path: Optional[str] = None) -> Iterator[str]:
        """Download ``key`` to a temp file and yield the local path.

        The temp file is deleted on exit::

            with bucket.fetch("data.csv") as path:
                df = pd.read_csv(path)
        """
        if temp_path is None:
            fd, temp_path = tempfile.mkstemp()
            os.close(fd)
        try:
            self._client.download_file(self._bucket, key, temp_path)
            yield temp_path
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @contextmanager
    def open(self, key: str, mode: str = "r") -> Iterator:
        """Download ``key`` and yield an open file handle::

            with bucket.open("notes.txt") as f:
                print(f.read())
        """
        fd, temp_path = tempfile.mkstemp()
        try:
            os.close(fd)
            self._client.download_file(self._bucket, key, temp_path)
            with open(temp_path, mode) as f:
                yield f
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def presigned_upload(self, key: str, expires_in: int = 3600) -> str:
        """Return a presigned URL that allows uploading to ``key``."""
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def presigned_download(self, key: str, expires_in: int = 3600) -> str:
        """Return a presigned URL that allows downloading ``key``."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
