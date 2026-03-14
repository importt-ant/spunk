from __future__ import annotations

from typing import Optional

import boto3


class SESIdentity:
    """Runtime accessor for a provisioned AWS SES identity.

    Wraps a verified SES sender identity (email address or domain) and
    exposes sending operations tied to that identity::

        ses = SESIdentity(identity="no-reply@acme.com", region="eu-west-1")
        ses.send("user@example.com", "Hello", "<p>Hello</p>", "Hello")

        # domain identity — send from any address on the domain:
        ses = SESIdentity(identity="acme.com", region="eu-west-1")
        ses.send("user@example.com", "Hi", "<p>Hi</p>", "Hi",
                 from_address="support@acme.com")
    """

    def __init__(
        self,
        identity: str,
        region: str,
        profile: Optional[str] = None,
    ) -> None:
        """
        :param identity: The verified SES identity — either a full email
            address (``no-reply@acme.com``) or a domain (``acme.com``).
            Used as the default sender address when ``from_address`` is
            not supplied on individual calls.
        :param region: AWS region where the identity is registered.
        :param profile: Optional named AWS profile.
        """
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self._client = session.client("ses", region_name=region)
        self._identity = identity

    # TODO: support more of the features of SES, like attachments, bulk sending with different content per recipient, templates, etc.

    @property
    def identity(self) -> str:
        """The verified SES identity (email address or domain)."""
        return self._identity

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        from_address: Optional[str] = None,
    ) -> dict:
        """Send an email from this identity.

        :param to: Recipient email address.
        :param subject: Email subject line.
        :param body_html: HTML version of the body.
        :param body_text: Plain-text version of the body.
        :param from_address: Override the sender address. Defaults to
            ``identity``. Required when ``identity`` is a domain rather
            than a full email address.
        """
        return self._client.send_email(
            Source=from_address or self._identity,
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
        from_address: Optional[str] = None,
    ) -> dict:
        """Send the same email to multiple recipients from this identity.

        :param recipients: List of recipient email addresses.
        :param subject: Email subject line.
        :param body_html: HTML version of the body.
        :param body_text: Plain-text version of the body.
        :param from_address: Override the sender address. Defaults to
            ``identity``.
        """
        return self._client.send_email(
            Source=from_address or self._identity,
            Destination={"ToAddresses": recipients},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {"Data": body_html},
                    "Text": {"Data": body_text},
                },
            },
        )

    def get_verification_status(self) -> str:
        """Return the verification status of this identity.

        :returns: One of ``"Pending"``, ``"Success"``, ``"Failed"``,
            ``"TemporaryFailure"``, or ``"NotStarted"``.
        """
        resp = self._client.get_identity_verification_attributes(
            Identities=[self._identity]
        )
        attrs = resp["VerificationAttributes"].get(self._identity, {})
        return attrs.get("VerificationStatus", "NotStarted")
