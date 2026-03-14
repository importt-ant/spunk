from __future__ import annotations

from typing import Dict, List, Literal, Optional, TYPE_CHECKING

from .aws_resource import AWSResource
from ...providers.aws import AWSProvider

if TYPE_CHECKING:
    import pulumi_aws as aws


class DynamoDBTableBuilder(AWSResource):
    """Pulumi resource builder for an AWS DynamoDB table.

    Typical usage inside a ``Service.resources()`` implementation::

        table = (
            DynamoDBTableBuilder("my-table", tenant_name, "my-service", provider)
            .with_hash_key("id")
            .add_attribute("id", "S")
            .add_attribute("status", "S")
            .add_gsi("status-index", hash_key="status")
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

        self._billing_mode: Literal["PAY_PER_REQUEST", "PROVISIONED"] = "PAY_PER_REQUEST"
        self._hash_key: Optional[str] = None
        self._range_key: Optional[str] = None
        self._attributes: List[Dict] = []
        self._global_secondary_indexes: List[Dict] = []
        self._local_secondary_indexes: List[Dict] = []

    def with_hash_key(self, key: str) -> "DynamoDBTableBuilder":
        """Set the partition (hash) key."""
        self._hash_key = key
        return self

    def with_range_key(self, key: str) -> "DynamoDBTableBuilder":
        """Set the sort (range) key."""
        self._range_key = key
        return self

    def with_billing_mode(
        self,
        mode: Literal["PAY_PER_REQUEST", "PROVISIONED"],
    ) -> "DynamoDBTableBuilder":
        """Override the default billing mode (PAY_PER_REQUEST)."""
        self._billing_mode = mode
        return self

    def add_attribute(
        self,
        name: str,
        attr_type: Literal["S", "N", "B"],
    ) -> "DynamoDBTableBuilder":
        """Declare an attribute that is referenced by a key or index."""
        self._attributes.append({"name": name, "type": attr_type})
        return self

    def add_gsi(
        self,
        index_name: str,
        hash_key: str,
        range_key: Optional[str] = None,
        projection_type: Literal["ALL", "KEYS_ONLY", "INCLUDE"] = "ALL",
        non_key_attributes: Optional[List[str]] = None,
    ) -> "DynamoDBTableBuilder":
        """Add a Global Secondary Index."""
        if projection_type == "INCLUDE" and not non_key_attributes:
            raise ValueError(
                "non_key_attributes must be provided when projection_type is 'INCLUDE'"
            )

        gsi: Dict = {
            "name": index_name,
            "hash_key": hash_key,
            "projection_type": projection_type,
        }
        if range_key:
            gsi["range_key"] = range_key
        if non_key_attributes:
            gsi["non_key_attributes"] = non_key_attributes

        self._global_secondary_indexes.append(gsi)
        return self

    def add_lsi(
        self,
        index_name: str,
        range_key: str,
        projection_type: Literal["ALL", "KEYS_ONLY", "INCLUDE"] = "ALL",
        non_key_attributes: Optional[List[str]] = None,
    ) -> "DynamoDBTableBuilder":
        """Add a Local Secondary Index."""
        if projection_type == "INCLUDE" and not non_key_attributes:
            raise ValueError(
                "non_key_attributes must be provided when projection_type is 'INCLUDE'"
            )

        lsi: Dict = {
            "name": index_name,
            "range_key": range_key,
            "projection_type": projection_type,
        }
        if non_key_attributes:
            lsi["non_key_attributes"] = non_key_attributes

        self._local_secondary_indexes.append(lsi)
        return self

    def declare(self) -> "aws.dynamodb.Table":
        """Declare the DynamoDB table to the Pulumi stack.

        Internal — invoked by ``Service.provision()``.
        """
        import pulumi
        import pulumi_aws as aws

        if not self._hash_key:
            raise ValueError(
                f"DynamoDBTable '{self.resource_name}': hash key must be set before invoking"
            )

        attributes = [aws.dynamodb.TableAttributeArgs(**a) for a in self._attributes]
        gsis = [aws.dynamodb.TableGlobalSecondaryIndexArgs(**g) for g in self._global_secondary_indexes]
        lsis = [aws.dynamodb.TableLocalSecondaryIndexArgs(**l) for l in self._local_secondary_indexes]

        kwargs: Dict = {
            "billing_mode": self._billing_mode,
            "hash_key": self._hash_key,
            "attributes": attributes,
            "tags": self._tags,
            "opts": pulumi.ResourceOptions(provider=self.provider.get()),
        }

        if self._range_key:
            kwargs["range_key"] = self._range_key
        if gsis:
            kwargs["global_secondary_indexes"] = gsis
        if lsis:
            kwargs["local_secondary_indexes"] = lsis

        return aws.dynamodb.Table(self.resource_name, **kwargs)
