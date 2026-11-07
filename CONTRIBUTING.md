# Contributing

Start with the [architecture](docs/ARCHITECTURE.md), [build instructions](docs/BUILDING.md) and [test guide](docs/TESTING.md). Use small, focused changes and describe the problem, affected files, verification and remaining limitations.

- Preserve original author credits, GPL obligations and [component-specific notices](THIRD_PARTY_NOTICES.md). Do not add binaries or assets without exact-version provenance, licensing and dependency review.
- Never include game files, payload binaries, credentials, DPAPI data, transaction journals, backups, logs or build caches in corresponding source.
- Use isolated synthetic fixtures for engine tests. Do not use a personal game installation as a test fixture or weaken path/hash/ownership/consent checks.
- Preserve CLI/API compatibility, component identities, transaction formats and matching-runtime recovery. Source moves and internal cleanup require tests and, when shipped code changes, a separate qualified development build.
- Keep published EXE/source ZIP/checksum assets immutable. Repository-only documentation may postdate those assets; see [source provenance](docs/SOURCE_PROVENANCE.md).
- Do not claim stock Windows, DPI, recovery or gameplay results that were not actually observed. File issues without private paths, logs containing personal information or credentials.

Release publication is handled by the project maintainer. This guide does not grant approval to publish changes or restore excluded components.
