from __future__ import annotations

from typing import Optional, Tuple, Dict, Any, TYPE_CHECKING

from .aws_resource import AWSResource
from ...providers.aws import AWSProvider

if TYPE_CHECKING:
    import pulumi_aws as aws


class SESIdentityBuilder(AWSResource):
    """Pulumi resource builder for an AWS SES sender identity.

    Verifies either an **email address** or a **domain**, and optionally
    configures DKIM signing and a sending configuration set.

    Typical usage inside a ``Service.resources()`` implementation::

        identity = (
            SESIdentityBuilder("no-reply@acme.com", tenant_name, "mailer", provider)
            .as_email()
        )

        # or for a full domain with DKIM:
        domain_identity = (
            SESIdentityBuilder("acme.com", tenant_name, "mailer", provider)
            .as_domain()
            .with_dkim()
            .with_configuration_set("acme-sending")
        )

    .. note::
        SES identity verification is asynchronous on AWS — after ``pulumi up``
        you still need to confirm the verification link (email) or add the DNS
        records (domain) before SES will allow sending.
    """

    def __init__(
        self,
        resource_name: str,
        tenant_name: str,
        service_name: str,
        provider: AWSProvider,
    ) -> None:
        super().__init__(resource_name, tenant_name, service_name, provider)
        self._identity_type: str = "email"   # "email" | "domain" make this into a literal
        self._enable_dkim: bool = False
        self._configuration_set_name: Optional[str] = None

    def as_email(self) -> "SESIdentityBuilder":
        """Verify a single email address identity (default).

        Use when ``resource_name`` is an email address such as
        ``no-reply@acme.com``.
        """
        self._identity_type = "email"
        return self

    def as_domain(self) -> "SESIdentityBuilder":
        """Verify a full domain identity.

        Use when ``resource_name`` is a bare domain such as ``acme.com``.
        After ``pulumi up``, add the returned DNS TXT records to your DNS
        zone to complete verification.
        """
        self._identity_type = "domain"
        return self

    def with_dkim(self) -> "SESIdentityBuilder":
        """Enable DKIM signing for this domain identity.

        Creates an ``aws.ses.DomainDkim`` resource alongside the identity.
        Only meaningful for domain identities — ignored for email identities.
        """
        self._enable_dkim = True
        return self

    def with_configuration_set(self, name: str) -> "SESIdentityBuilder":
        """Create and associate a named SES configuration set.

        Configuration sets let you attach event destinations (SNS, CloudWatch,
        Kinesis) to track opens, clicks, bounces, and complaints.

        :param name: The name of the configuration set to create.
        """
        self._configuration_set_name = name
        return self

    def declare(self) -> Any:
        """Register SES identity (and optional DKIM / configuration set) with Pulumi."""
        import pulumi_aws as aws

        provider_resource = self.provider.get()
        opts = {"provider": provider_resource} if provider_resource else {}

        if self._identity_type == "domain":
            identity = aws.ses.DomainIdentity(
                self.resource_name,
                domain=self.resource_name,
                opts=opts,
            )
            if self._enable_dkim:
                aws.ses.DomainDkim(
                    f"{self.resource_name}-dkim",
                    domain=identity.domain,
                    opts=opts,
                )
        else:
            identity = aws.ses.EmailIdentity(
                self.resource_name,
                email=self.resource_name,
                opts=opts,
            )

        if self._configuration_set_name:
            aws.ses.ConfigurationSet(
                self._configuration_set_name,
                name=self._configuration_set_name,
                opts=opts,
            )

        return identity

    def accessor(self) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """Return the descriptor for the :class:`~spunk.accessors.aws.ses_identity.SESIdentity` accessor.

        ``resource_name`` is passed as ``identity`` to the accessor, so the
        same value used to register the identity in Pulumi (e.g.
        ``no-reply@acme.com`` or ``acme.com``) is what the accessor sends from.
        """
        return (
            "spunk.accessors.aws.ses_identity",
            "SESIdentity",
            {
                "identity": self.resource_name,
                "region": self.provider.region,
                "profile": self.provider.profile,
            },
        )
