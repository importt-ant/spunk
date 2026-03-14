# spunk

A general-purpose [Pulumi](https://www.pulumi.com/) framework for Python.

`spunk` gives you a structured way to define cloud infrastructure as typed Python
classes, provision it with a single command, and get a fully-typed AWS SDK
auto-generated so the rest of your codebase can interact with the infrastructure
without ever copy-pasting ARNs or table names.

## Quick start

```python
from spunk import Tenant, Service
from spunk.providers import AWSProvider
from spunk.resources import DynamoDBTableBuilder, S3BucketBuilder

aws = AWSProvider(pulumi_name="acme-aws", region="eu-west-1")

class ItemsService(Service):
    def resources(self, provider):
        return [
            DynamoDBTableBuilder("items-table", self._tenant_name, self.name(), provider)
                .with_hash_key("pk"),
            S3BucketBuilder("uploads", self._tenant_name, self.name(), provider)
                .enable_versioning(),
        ]

acme = Tenant("acme").add(ItemsService("acme"), aws)
acme.deploy()

TENANTS = [acme]
```

Then run:

```bash
spunk up        # provision + save manifest + generate SDK
spunk preview   # dry-run
spunk gen       # regenerate SDK from stored manifest (no infra code needed)
```

## How it works

```
Tenant
 └── Service  (groups related resources, declares dependencies)
      └── Resource  (wraps a single Pulumi/AWS resource)
           └── Accessor  (generated boto3 helper for runtime use)
```

1. **`spunk up`** validates dependencies, runs `pulumi up`, persists a manifest to S3,
   and optionally regenerates the typed SDK locally.
2. **`spunk gen`** pulls the manifest from S3 and regenerates the SDK — no original
   infrastructure code required.
