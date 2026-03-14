from __future__ import annotations

import json
from typing import List, Optional, Tuple

from .service import Service
from .providers.provider import Provider


class DependencyError(Exception):
    """Raised when a service's declared dependencies are not satisfied."""
    pass


class Tenant:
    """Represents a tenant and the services provisioned for them.

    Build up a tenant programmatically using ``add()``, then call ``deploy()``
    to register all resources with the Pulumi stack::

        tenant = (
            Tenant("acme")
            .add(Scheduler("acme"), aws_provider)
            .add(Honeycomb("acme"), aws_provider)
        )
        tenant.deploy()
    """

    def __init__(self, name: str) -> None:
        self.name: str = name
        self._services: List[Tuple[Service, Provider]] = []

    @property
    def services(self) -> List[Service]:
        """Read-only list of registered services."""
        return [svc for svc, _ in self._services]

    def add(self, service: Service, provider: Provider) -> "Tenant":
        """Register a service and the provider it should be provisioned with.

        Returns ``self`` so calls can be chained.
        """
        self._services.append((service, provider))
        return self

    def _check_dependencies(self) -> None:
        all_services = self.services
        for service in all_services:
            missing = service.missing_dependencies(all_services)
            if missing:
                names = ", ".join(m.__name__ for m in missing)
                raise DependencyError(
                    f"Service '{service.name()}' requires [{names}] but "
                    f"they have not been added. Call .add() with those services first."
                )

    def deploy(self) -> None:
        """Declare all services and their resources to the Pulumi stack.

        Validates dependencies first, then provisions each service in
        registration order.
        """
        self._check_dependencies()
        for service, provider in self._services:
            print(f"Provisioning {service.name()} for tenant {self.name}...")
            service._tenant_name = self.name
            service.provision(provider)

    def generate(self, output_dir: str) -> None:
        """Generate a typed SDK package for this tenant into ``output_dir``."""
        from .codegen import generate as _generate
        _generate(self, output_dir)

    # ------------------------------------------------------------------
    # Manifest: serialise / store / restore accessor descriptors
    # ------------------------------------------------------------------

    def to_manifest(self) -> dict:
        """Serialise this tenant's accessor descriptors to a plain dict.

        The manifest captures everything needed to regenerate the typed SDK
        package without requiring the original infrastructure code::

            manifest = tenant.to_manifest()
            # → {
            #     "version": "1",
            #     "tenant": "acme",
            #     "services": [
            #         {
            #             "name": "ExampleService",
            #             "snake": "example_service",
            #             "pascal": "ExampleService",
            #             "resources": [
            #                 {
            #                     "instance_name": "acme_items",
            #                     "accessor_module": "spunk.accessors.aws.dynamodb_table",
            #                     "accessor_class": "DynamoDBTable",
            #                     "kwargs": {"resource_name": "acme-items", ...}
            #                 }
            #             ]
            #         }
            #     ]
            # }
        """
        from .codegen import _to_snake_case, _to_pascal_case

        services = []
        for service, provider in self._services:
            resources = []
            for resource in service.resources(provider):
                result = resource.accessor()
                if result is None:
                    continue
                module_path, class_name, kwargs = result
                resources.append({
                    "instance_name": _to_snake_case(resource.resource_name),
                    "accessor_module": module_path,
                    "accessor_class": class_name,
                    "kwargs": kwargs,
                })
            services.append({
                "name": service.name(),
                "snake": _to_snake_case(service.name()),
                "pascal": _to_pascal_case(service.name()),
                "resources": resources,
            })

        return {
            "version": "1",
            "tenant": self.name,
            "services": services,
        }

    def save_manifest(
        self,
        bucket: str,
        key: Optional[str] = None,
        profile: Optional[str] = None,
        region: Optional[str] = None,
    ) -> str:
        """Serialise and upload this tenant's manifest to S3.

        :param bucket: S3 bucket name.
        :param key: Object key. Defaults to ``spunk/<tenant_name>.json``.
        :param profile: AWS profile name (optional).
        :param region: AWS region (optional).
        :returns: The S3 key the manifest was written to.
        """
        import boto3

        key = key or f"spunk/{self.name}.json"
        body = json.dumps(self.to_manifest(), indent=2).encode()

        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        kwargs = {}
        if region:
            kwargs["region_name"] = region
        session.client("s3", **kwargs).put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        return key

    @staticmethod
    def load_manifest(
        bucket: str,
        key: str,
        profile: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict:
        """Download and deserialise a tenant manifest from S3.

        :param bucket: S3 bucket name.
        :param key: Object key (e.g. ``spunk/acme.json``).
        :param profile: AWS profile name (optional).
        :param region: AWS region (optional).
        :returns: The manifest dict, suitable for :func:`~spunk.codegen.from_manifest`.

        Example::

            manifest = Tenant.load_manifest("my-bucket", "spunk/acme.json")
            from spunk.codegen import from_manifest
            from_manifest(manifest, "infra/")
        """
        import boto3

        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        kwargs = {}
        if region:
            kwargs["region_name"] = region
        response = session.client("s3", **kwargs).get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read())

