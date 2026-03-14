# Service

Abstract base class for all services.  Subclass `Service`, implement
`resources()`, and optionally override `dependencies()` to declare ordering
constraints between services.

::: spunk.service.Service
