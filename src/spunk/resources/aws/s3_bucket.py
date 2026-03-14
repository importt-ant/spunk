from __future__ import annotations

import hashlib
from typing import Dict, List, Literal, Optional, TYPE_CHECKING

from .aws_resource import AWSResource
from ...providers.aws import AWSProvider

if TYPE_CHECKING:
    import pulumi_aws as aws


class S3BucketBuilder(AWSResource):
    """Pulumi resource builder for an AWS S3 bucket.

    Typical usage inside a ``Service.resources()`` implementation::

        bucket = (
            S3BucketBuilder("my-bucket", tenant_name, "my-service", provider)
            .with_versioning()
            .add_cors_rule(["GET", "PUT"], ["*"])
        )

    The instance is declared (``declare()``) internally by the service.
    """

    def __init__(
        self,
        resource_name: str,
        tenant_name: str,
        service_name: str,
        provider: AWSProvider,
    ) -> None:
        super().__init__(resource_name, tenant_name, service_name, provider)

        self._versioning_enabled: bool = False
        self._block_public_access: bool = True
        self._cors_rules: List[Dict] = []
        self._lifecycle_rules: List[Dict] = []

    def with_versioning(self) -> "S3BucketBuilder":
        """Enable object versioning on the bucket."""
        self._versioning_enabled = True
        return self

    def with_public_access(self) -> "S3BucketBuilder":
        """Disable the default public-access block (e.g. for static sites)."""
        self._block_public_access = False
        return self

    def add_cors_rule(
        self,
        allowed_methods: List[Literal["GET", "PUT", "POST", "DELETE", "HEAD"]],
        allowed_origins: List[str],
        allowed_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        max_age_seconds: Optional[int] = None,
    ) -> "S3BucketBuilder":
        """Append a CORS rule to the bucket configuration."""
        rule: Dict = {
            "allowed_methods": allowed_methods,
            "allowed_origins": allowed_origins,
        }
        if allowed_headers:
            rule["allowed_headers"] = allowed_headers
        if expose_headers:
            rule["expose_headers"] = expose_headers
        if max_age_seconds:
            rule["max_age_seconds"] = max_age_seconds

        self._cors_rules.append(rule)
        return self

    def add_lifecycle_rule(
        self,
        rule_id: str,
        enabled: bool = True,
        prefix: Optional[str] = None,
        expiration_days: Optional[int] = None,
        transition_days: Optional[int] = None,
        transition_storage_class: Optional[
            Literal[
                "GLACIER",
                "DEEP_ARCHIVE",
                "INTELLIGENT_TIERING",
                "STANDARD_IA",
                "ONEZONE_IA",
            ]
        ] = None,
    ) -> "S3BucketBuilder":
        """Append a lifecycle rule to the bucket configuration."""
        rule: Dict = {"id": rule_id, "enabled": enabled}

        if prefix:
            rule["prefix"] = prefix
        if expiration_days:
            rule["expiration"] = {"days": expiration_days}
        if transition_days and transition_storage_class:
            rule["transitions"] = [
                {"days": transition_days, "storage_class": transition_storage_class}
            ]

        self._lifecycle_rules.append(rule)
        return self

    def declare(self) -> "aws.s3.BucketV2":
        """Declare the S3 bucket and its sub-resources to the Pulumi stack.

        Internal — invoked by ``Service.provision()``.
        """
        import pulumi
        import pulumi_aws as aws

        opts = pulumi.ResourceOptions(provider=self.provider.get())

        bucket = aws.s3.BucketV2(
            self.resource_name,
            bucket=self.resource_name,
            tags=self._tags,
            opts=opts,
        )

        if self._versioning_enabled:
            aws.s3.BucketVersioningV2(
                f"{self.resource_name}-versioning",
                bucket=bucket.id,
                versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(
                    status="Enabled"
                ),
                opts=opts,
            )

        if self._block_public_access:
            aws.s3.BucketPublicAccessBlock(
                f"{self.resource_name}-public-access-block",
                bucket=bucket.id,
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True,
                opts=opts,
            )

        if self._cors_rules:
            aws.s3.BucketCorsConfigurationV2(
                f"{self.resource_name}-cors",
                bucket=bucket.id,
                cors_rules=[aws.s3.BucketCorsConfigurationV2CorsRuleArgs(**r) for r in self._cors_rules],
                opts=opts,
            )

        if self._lifecycle_rules:
            aws.s3.BucketLifecycleConfigurationV2(
                f"{self.resource_name}-lifecycle",
                bucket=bucket.id,
                rules=self._lifecycle_rules,
                opts=opts,
            )

        return bucket
