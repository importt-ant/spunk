from __future__ import annotations

from typing import Optional

import boto3


class SES:
    """Runtime accessor for AWS Simple Email Service.

    Instantiated by generated SDK code or directly::

        ses = SES(region="eu-west-1", from_email="no-reply@example.com")
        ses.send("user@example.com", "Hello", "<p>Hello</p>", "Hello")
    """

    def __init__(
        self,
        region: str,
        from_email: str,
        profile: Optional[str] = None,
    ) -> None:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self._client = session.client("ses", region_name=region)
        self._from_email = from_email

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        from_email: Optional[str] = None,
    ) -> dict:
        """Send an email via SES.

        :param to: Recipient email address.
        :param subject: Email subject line.
        :param body_html: HTML version of the body.
        :param body_text: Plain-text version of the body.
        :param from_email: Override the default sender address.
        """
        return self._client.send_email(
            Source=from_email or self._from_email,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {"Data": body_html},
                    "Text": {"Data": body_text},
                },
            },
        )

    def send_bulk(
        self,
        recipients: list[str],
        subject: str,
        body_html: str,
        body_text: str,
        from_email: Optional[str] = None,
    ) -> dict:
        """Send the same email to multiple recipients."""
        return self._client.send_email(
            Source=from_email or self._from_email,
            Destination={"ToAddresses": recipients},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {"Data": body_html},
                    "Text": {"Data": body_text},
                },
            },
        )
