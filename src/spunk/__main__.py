"""Infrastructure provisioning for Pulumi.

This file is the Pulumi entrypoint (referenced by Pulumi.yaml) **and** the
``spunk`` CLI entrypoint (referenced by ``entrypoint:`` in spunk.yaml).

Pulumi executes this module directly when running ``pulumi up / preview``.
The ``spunk`` CLI also imports it to read the ``TENANTS`` list for pre-flight
validation, post-deploy manifest saving, and optional SDK generation.

Required module-level names
----------------------------
``TENANTS``
    A plain Python list of all :class:`~spunk.Tenant` instances that were
    deployed in this module.  The ``spunk`` CLI reads this list; it is **not**
    used by Pulumi itself.

Example
-------
::

    from spunk import Tenant, Service
    from spunk.providers import AWSProvider
    from spunk.resources import DynamoDBTableBuilder, S3BucketBuilder

    # --- providers -----------------------------------------------------------
    aws = AWSProvider(
        pulumi_name="acme-aws",
        region="eu-west-1",
        profile="acme-dev",
    )

    # --- services (define your own in separate modules) ----------------------
    class ItemsService(Service):
        def resources(self, provider):
            return [
                DynamoDBTableBuilder("items-table", self._tenant_name, self.name(), provider)
                    .with_hash_key("pk"),
                S3BucketBuilder("uploads", self._tenant_name, self.name(), provider)
                    .enable_versioning(),
            ]

    # --- tenant --------------------------------------------------------------
    acme = (
        Tenant("acme")
        .add(ItemsService("acme"), aws)
    )

    # deploy() registers all resources with the Pulumi engine.
    # It must be called at module level so Pulumi sees the resources when it
    # imports this file.
    acme.deploy()

    # TENANTS is read by the spunk CLI — keep it in sync with what you deployed.
    TENANTS = [acme]
"""
