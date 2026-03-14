"""spunk CLI — wraps Pulumi with pre/post-flight logic.

Commands
--------
spunk up [-- PULUMI_ARGS...]
    Run pre-flight validation, then ``pulumi up``, then save each tenant
    manifest to S3 and optionally regenerate the local typed SDK.

spunk gen [``--tenant NAME``] [``--output DIR``]
    Fetch a manifest from S3 and regenerate the typed SDK locally.
    Does not require the original infrastructure code.

spunk preview | destroy | stack | ... [PULUMI_ARGS...]
    Thin wrappers that forward directly to Pulumi, with pre-flight
    validation where it makes sense.

Configuration — spunk.yaml
--------------------------
Place a ``spunk.yaml`` file in the project root (next to ``Pulumi.yaml``)::

    # spunk.yaml
    entrypoint: __main__.py      # file that exposes TENANTS = [...]
    state_bucket: my-state-bucket
    state_prefix: spunk/         # key prefix inside the bucket; default "spunk/"
    generate:
      output: infra/             # if set, run generate after every 'spunk up'
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import yaml


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

SPUNK_YAML = "spunk.yaml"


def _load_config(path: str = SPUNK_YAML) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open() as f:
        return yaml.safe_load(f) or {}


def _require(cfg: dict, *keys: str) -> str:
    for k in keys:
        cfg = cfg.get(k)
        if cfg is None:
            raise click.ClickException(
                f"Missing required config key '{'.'.join(keys)}' in {SPUNK_YAML}"
            )
    return cfg


# ---------------------------------------------------------------------------
# Tenant loader
# ---------------------------------------------------------------------------

def _load_tenants(cfg: dict) -> list:
    """Import the user's entrypoint module and return its TENANTS list."""
    entrypoint = cfg.get("entrypoint", "__main__.py")
    ep = Path(entrypoint)
    if not ep.exists():
        raise click.ClickException(
            f"Entrypoint '{entrypoint}' not found. "
            f"Set 'entrypoint' in {SPUNK_YAML} or create {entrypoint}."
        )

    import importlib.util
    spec = importlib.util.spec_from_file_location("_spunk_entrypoint", ep)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        raise click.ClickException(f"Failed to import '{entrypoint}': {exc}") from exc

    tenants = getattr(mod, "TENANTS", None)
    if tenants is None:
        raise click.ClickException(
            f"'{entrypoint}' must define a module-level list: TENANTS = [my_tenant, ...]"
        )
    return tenants


# ---------------------------------------------------------------------------
# Pulumi subprocess helper
# ---------------------------------------------------------------------------

def _pulumi(*args: str, check: bool = True) -> int:
    """Run a pulumi command, streaming output. Returns exit code."""
    result = subprocess.run(["pulumi", *args])
    if check and result.returncode != 0:
        raise click.ClickException(f"pulumi {args[0]} failed (exit {result.returncode})")
    return result.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def main() -> None:
    """spunk — Pulumi wrapper with tenant-aware provisioning and SDK generation."""


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("pulumi_args", nargs=-1, type=click.UNPROCESSED)
@click.option("--no-generate", is_flag=True, default=False,
              help="Skip SDK generation even if 'generate.output' is configured.")
def up(pulumi_args: tuple, no_generate: bool) -> None:
    """Provision infrastructure and update the tenant manifest in S3."""
    cfg = _load_config()
    tenants = _load_tenants(cfg)

    # pre-flight: validate all dependency graphs
    from spunk.tenant import DependencyError
    for tenant in tenants:
        try:
            tenant._check_dependencies()
        except DependencyError as e:
            raise click.ClickException(str(e)) from e

    click.echo("✓ Dependency checks passed")

    # hand off to pulumi
    _pulumi("up", *pulumi_args)

    # post-flight: save manifests
    bucket = cfg.get("state_bucket")
    prefix = cfg.get("state_prefix", "spunk/")
    if bucket:
        for tenant in tenants:
            key = f"{prefix.rstrip('/')}/{tenant.name}.json"
            saved = tenant.save_manifest(bucket=bucket, key=key)
            click.echo(f"✓ Manifest saved → s3://{bucket}/{saved}")
    else:
        click.echo(
            "⚠  No 'state_bucket' in spunk.yaml — manifests not saved. "
            "Add 'state_bucket: <bucket>' to enable remote SDK generation."
        )

    # post-flight: generate SDK
    output_dir = cfg.get("generate", {}).get("output") if not no_generate else None
    if output_dir:
        for tenant in tenants:
            tenant.generate(output_dir)
            click.echo(f"✓ SDK generated → {output_dir}")


@main.command()
@click.option("--tenant", "tenant_name", default=None,
              help="Tenant name to generate. Fetches <prefix>/<name>.json from S3.")
@click.option("--output", "output_dir", default=None,
              help="Output directory for the generated SDK. Overrides spunk.yaml.")
@click.option("--bucket", "bucket", default=None,
              help="S3 bucket. Overrides spunk.yaml 'state_bucket'.")
def gen(tenant_name: Optional[str], output_dir: Optional[str], bucket: Optional[str]) -> None:
    """Fetch a manifest from S3 and regenerate the typed SDK locally."""
    from spunk.tenant import Tenant
    from spunk.generator import from_manifest

    cfg = _load_config()
    bucket = bucket or cfg.get("state_bucket")
    if not bucket:
        raise click.ClickException(
            "No S3 bucket specified. Pass --bucket or set 'state_bucket' in spunk.yaml."
        )

    prefix = cfg.get("state_prefix", "spunk/").rstrip("/")
    output_dir = output_dir or cfg.get("generate", {}).get("output", "infra/")

    if tenant_name:
        names = [tenant_name]
    else:
        # discover all manifests under the prefix
        import boto3
        client = boto3.client("s3")
        resp = client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/")
        names = [
            Path(obj["Key"]).stem
            for obj in resp.get("Contents", [])
            if obj["Key"].endswith(".json")
        ]
        if not names:
            raise click.ClickException(
                f"No manifests found at s3://{bucket}/{prefix}/. "
                "Run 'spunk up' first to save manifests."
            )

    for name in names:
        key = f"{prefix}/{name}.json"
        click.echo(f"Fetching s3://{bucket}/{key} ...")
        manifest = Tenant.load_manifest(bucket=bucket, key=key)
        from_manifest(manifest, output_dir)
        click.echo(f"✓ SDK generated for '{name}' → {output_dir}")


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("pulumi_args", nargs=-1, type=click.UNPROCESSED)
def preview(pulumi_args: tuple) -> None:
    """Preview infrastructure changes (pulumi preview)."""
    cfg = _load_config()
    tenants = _load_tenants(cfg)
    from spunk.tenant import DependencyError
    for tenant in tenants:
        try:
            tenant._check_dependencies()
        except DependencyError as e:
            raise click.ClickException(str(e)) from e
    click.echo("✓ Dependency checks passed")
    code = _pulumi("preview", *pulumi_args, check=False)
    sys.exit(code)


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("pulumi_args", nargs=-1, type=click.UNPROCESSED)
def destroy(pulumi_args: tuple) -> None:
    """Destroy all provisioned infrastructure (pulumi destroy)."""
    code = _pulumi("destroy", *pulumi_args, check=False)
    sys.exit(code)


@main.command(name="stack",
              context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("pulumi_args", nargs=-1, type=click.UNPROCESSED)
def stack(pulumi_args: tuple) -> None:
    """Manage Pulumi stacks (pulumi stack ...)."""
    code = _pulumi("stack", *pulumi_args, check=False)
    sys.exit(code)


@main.command(name="run",
              context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def run(args: tuple) -> None:
    """Pass any command directly to pulumi (e.g. spunk run -- config set ...)."""
    code = _pulumi(*args, check=False)
    sys.exit(code)
