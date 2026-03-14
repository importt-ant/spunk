from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .provider import Provider

if TYPE_CHECKING:
    import pulumi_aws as aws


class AWSProvider(Provider):
    """AWS cloud provider wrapper.

    Holds region and optional credential configuration. The underlying
    ``pulumi_aws.Provider`` object is created lazily on first ``get()`` call.

    One instance should be shared across all AWS resources for a given
    tenant, ensuring they all land in the same region under the same identity.

    Usage::

        provider = AWSProvider(pulumi_name="my-tenant-aws", region="eu-west-1")

        # pass to an AWSResource builder:
        DynamoDBTable("my-table", tenant_name, service_name, provider)
    """

    def __init__(
        self,
        pulumi_name: str,
        region: str,
        profile: Optional[str] = None,
        role_arn: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.pulumi_name: str = pulumi_name
        self.region: str = region
        self.profile: Optional[str] = profile
        self.role_arn: Optional[str] = role_arn

    def _create(self) -> "aws.Provider":
        import pulumi_aws as aws

        kwargs = {"region": self.region}
        if self.profile:
            kwargs["profile"] = self.profile
        if self.role_arn:
            kwargs["assume_role"] = aws.ProviderAssumeRoleArgs(role_arn=self.role_arn)

        return aws.Provider(self.pulumi_name, **kwargs)
