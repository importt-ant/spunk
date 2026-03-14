"""Quick smoke-test for codegen — no Pulumi or AWS credentials required.

Run from the repo root:
    python test_codegen.py

What it tests:
- A minimal Service with DynamoDB and S3 resources can be defined.
- Tenant.generate() writes the expected package structure.
- Generated files import from spunk.accessors with correct class names and kwargs.
- The generated package is importable and instantiates correctly.
"""
import sys
import shutil
import importlib
import importlib.util
from pathlib import Path

# make sure src/ is on the path when running directly
REPO = Path(__file__).parent
sys.path.insert(0, str(REPO / "src"))

from spunk import Tenant, Service
from spunk.providers import AWSProvider
from spunk.resources.aws import DynamoDBTableBuilder, S3BucketBuilder


# ---------------------------------------------------------------------------
# Define a minimal test service
# ---------------------------------------------------------------------------

class ExampleService(Service):
    def resources(self, provider):
        return [
            DynamoDBTableBuilder("acme-items", self._tenant_name, self.name(), provider)
            .with_hash_key("id")
            .add_attribute("id", "S"),

            S3BucketBuilder("acme-uploads", self._tenant_name, self.name(), provider)
            .with_versioning(),
        ]


# ---------------------------------------------------------------------------
# Build tenant and generate SDK
# ---------------------------------------------------------------------------

provider = AWSProvider(
    pulumi_name="test-provider",
    region="eu-west-1",
    profile=None,
)

tenant = Tenant("acme").add(ExampleService("acme"), provider)

OUT = REPO / "test_infra"
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir()

print(f"Generating SDK into: {OUT}\n")
tenant.generate(str(OUT))

# ---------------------------------------------------------------------------
# Print generated files
# ---------------------------------------------------------------------------
for p in sorted(OUT.rglob("*.py")):
    rel = p.relative_to(OUT)
    bar = "─" * max(0, 60 - len(str(rel)))
    print(f"── {rel} {bar}")
    print(p.read_text())

# ---------------------------------------------------------------------------
# Import the generated package and check types
# ---------------------------------------------------------------------------
sys.path.insert(0, str(OUT))
import importlib

# load leaf → root so parent packages exist when children are loaded
for p in sorted(OUT.rglob("*.py"), reverse=True):
    parts = p.relative_to(OUT).with_suffix("").parts
    # normalise __init__ → package name only
    mod_name = ".".join(parts[:-1]) if parts[-1] == "__init__" else ".".join(parts)
    if not mod_name:
        mod_name = "infra"
    spec = importlib.util.spec_from_file_location(
        mod_name, p,
        submodule_search_locations=[str(p.parent)] if p.name == "__init__.py" else None,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)

from spunk.accessors.aws.dynamodb_table import DynamoDBTable as DDBAccessor
from spunk.accessors.aws.s3_bucket import S3Bucket as S3Accessor


svc = sys.modules["acme.example_service"].ExampleService()
assert isinstance(svc.acme_items, DDBAccessor), f"expected DynamoDBTable, got {type(svc.acme_items)}"
assert isinstance(svc.acme_uploads, S3Accessor), f"expected S3Bucket, got {type(svc.acme_uploads)}"

print("✓ acme.example_service.ExampleService().acme_items   →", type(svc.acme_items).__name__)
print("✓ acme.example_service.ExampleService().acme_uploads →", type(svc.acme_uploads).__name__)

tenant_cls = sys.modules["acme"].Acme()
print("✓ acme.Acme().example_service                        →", type(tenant_cls.example_service).__name__)

# ---------------------------------------------------------------------------
# Clean up
# ---------------------------------------------------------------------------
shutil.rmtree(OUT)
print(f"\n✓ Cleaned up {OUT}")

