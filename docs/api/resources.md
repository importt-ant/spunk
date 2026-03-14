# Resources

Resources are thin wrappers around Pulumi resource constructors.  Each
builder accumulates configuration through a fluent API and registers itself
with the Pulumi engine when `declare()` is called (done automatically by
`Service.provision()`).

## Base classes

::: spunk.resources.resource.Resource

::: spunk.resources.aws.resource.AWSResource

## AWS resource builders

::: spunk.resources.aws.dynamodb_table.DynamoDBTableBuilder

::: spunk.resources.aws.s3_bucket.S3BucketBuilder
