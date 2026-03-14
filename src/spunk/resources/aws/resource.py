from __future__ import annotations

from typing import Dict

from ..resource import Resource
from ...providers.aws import AWSProvider


class AWSResource(Resource):
    """Base class for all AWS infrastructure resource builders.

    Handles provider forwarding, tenant/service tagging, and resource naming.
    Concrete subclasses (e.g. ``DynamoDBTableBuilder``, ``S3BucketBuilder``)
    extend this with builder methods and a ``declare()`` implementation.
    """

    def __init__(
        self,
        resource_name: str,
        tenant_name: str,
        service_name: str,
        provider: AWSProvider,
    ) -> None:
        super().__init__(resource_name, tenant_name, service_name)
        self.provider: AWSProvider = provider

        # default tags applied to every resource; extend via add_tag()
        self._tags: Dict[str, str] = {
            "tenant": tenant_name,
            "service": service_name,
            "managedby": "pulumi w spunk",
        }

    def add_tag(self, key: str, value: str) -> "AWSResource":
        """Attach an arbitrary AWS tag to this resource."""
        self._tags[key] = value
        return self

    def accessor(self):
        """Return a codegen descriptor pointing to the matching accessor class.

        Derives the module path by replacing ``.resources.`` with ``.accessors.``
        in this class's module. The accessor class name is derived from the
        builder class name with the ``Builder`` suffix stripped.

        E.g. ``spunk.resources.aws.dynamodb_table.DynamoDBTableBuilder``
          →  ``spunk.accessors.aws.dynamodb_table.DynamoDBTable``
        """
        module = type(self).__module__.replace(".resources.", ".accessors.", 1)
        class_name = type(self).__name__
        if class_name.endswith("Builder"):
            class_name = class_name[:-7]
        return (
            module,
            class_name,
            {
                "resource_name": self.resource_name,
                "region": self.provider.region,
                "profile": self.provider.profile,
            },
        )
