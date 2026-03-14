"""Example spunk entrypoint.

Copy this file to your project, rename it (e.g. ``__main__.py``), fill in
your own services and resources, then point ``spunk.yaml`` at it via the
``entrypoint:`` key.

This file doubles as:
  * The **Pulumi** entrypoint — Pulumi imports it to discover resources.
  * The **spunk CLI** entrypoint — ``spunk up / preview`` read ``TENANTS``.

Run:
  pulumi up          # provision directly via Pulumi
  spunk up           # provision via spunk (adds manifest saving + SDK gen)
  spunk preview      # dry-run
"""
from __future__ import annotations

from spunk import Service, Tenant
from spunk.providers import AWSProvider
from spunk.resources import DynamoDBTableBuilder, S3BucketBuilder

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

aws = AWSProvider(
    pulumi_name="example-aws",
    region="eu-west-1",
    # profile="my-aws-profile",   # uncomment to use a named AWS profile
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


class ItemsService(Service):
    """Manages the core items table and upload bucket."""

    def resources(self, provider):
        return [
            DynamoDBTableBuilder(
                "items-table", self._tenant_name, self.name(), provider
            ).with_hash_key("pk"),
            S3BucketBuilder(
                "uploads", self._tenant_name, self.name(), provider
            ).enable_versioning(),
        ]


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

example = (
    Tenant("example")
    .add(ItemsService("example"), aws)
)

# deploy() is called at module level so Pulumi sees every resource when it
# imports this file during `pulumi up`.
example.deploy()

# TENANTS is the list the spunk CLI reads — keep it in sync.
TENANTS = [example]
