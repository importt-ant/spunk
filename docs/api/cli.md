# CLI

The `spunk` command-line interface wraps Pulumi with pre/post-flight logic and
glues provisioning to manifest saving and SDK generation.

Configuration is read from `spunk.yaml` in the project root.

```yaml
# spunk.yaml
entrypoint: __main__.py   # file that exposes TENANTS = [...]
state_bucket: my-state-bucket
state_prefix: spunk/      # key prefix inside the bucket; default "spunk/"
generate:
  output: infra/          # if set, run generate after every 'spunk up'
```

::: spunk.cli
