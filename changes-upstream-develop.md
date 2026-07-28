# Changes from upstream develop

## Fixed

- Prevent a false negative when resolving a primary device from virtual chassis members by checking all members for a primary IP before failing, and harden active-status detection across status representations. (local uncommitted changes)
- Replace import-time dependency failures in API views with runtime dependency checks and return a service-unavailable response when required modules are missing. (local uncommitted changes)

## Changed

- Standardize test classes on Nautobot base test classes by migrating processor, content type, and output filter tests away from Django/unittest base classes. (local uncommitted changes)
- Improve job timestamp handling by using timezone-aware now values via Django timezone utilities. (local uncommitted changes)
- Replace startup print statements with structured logging in signal handlers for clearer operational diagnostics. (local uncommitted changes)

## Dependencies

- Update project metadata to declare Python 3.14 support and widen the supported Python range to include 3.14 releases. (local uncommitted changes)

## Housekeeping

- Align runtime checks and startup messaging behavior with more resilient production defaults while preserving existing API and job behavior. (local uncommitted changes)
