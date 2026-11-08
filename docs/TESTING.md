# Test guide

Run source tests only in a separate development workspace with its required verified inputs. Some tests create isolated fixtures under out; tests are not read-only commands and do not qualify a real game. Do not import build scripts for test discovery: some perform top-level build actions.

## Existing entry points

From the repository root, with a compatible development Python:

```powershell
New-Item -ItemType Directory -Force out | Out-Null
python -B -c "import sys,unittest; sys.path[:0]=['src','tools','tests']; suite=unittest.defaultTestLoader.discover('tests',pattern='test_*.py'); result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())"
python -B src/installer/ui-prototype/check_source.py
```

The full-suite command sets explicit source/tool imports before discovery; plain discovery can fail to import the first module. Use a short isolated development path: deeply nested synthetic backup paths can exceed the existing Windows path limit. This is a test-environment requirement, not permission to relax path checks.

The final command runs separate wizard source guards; it is not included by tests-only discovery. `tools/run_source_tests.py` runs only four named modules and must not be reported as the full regression. Optional-component tests need separately staged, exact verified payloads; the public source export intentionally omits binary payloads/toolchains. Missing inputs are not permission to substitute DLLs.

Frozen-backend qualification uses [qualify_dev110_packaged.py](../tools/qualify_dev110_packaged.py) with an explicit verified bundle and a fresh report directory. It executes synthetic transactions and must be separately authorized/prepared. Source checks cannot replace frozen/native/resource qualification or actual wizard testing.

## Active development source alignment

Phase10C1 separates published v1.1.0 metadata from the preserved development/candidate records and immutable build-time recipe. Release-sync checks validate both current publication and historical identities. The active source-export allowlist includes the post-release guides and reviewed current bytes; it describes a development source revision, not the published source ZIP.

The historical root `SOURCE_SHA256SUMS.txt` and released archives remain unchanged. Use `python -B tools/source_export_plan.py` for read-only validation of the active source list. Hash mismatches and unapproved paths must still fail; only an explicitly reviewed update may refresh a pin. No new source ZIP or installer is produced by this alignment.

## Result reporting

Record exact command, case count, input/source revision and failures. Keep owner-reported gameplay separate from independent observations. Recovery retesting, additional DPI and stock Windows remain unverified without new evidence; the unsigned EXE is not a compatibility guarantee. See [release readiness](RELEASE_READINESS.md), [clean Windows checklist](CLEAN_WINDOWS_TESTING.md) and [recovery](RECOVERY.md).

## v1.1.1 source preparation

The active recipe defaults to FINAL111/version 1.1.1. Tests separately validate the immutable FINAL110/version 1.1.0 recipe and published v1.0.0/v1.1.0 identities. Both relocated transports/legacy imports remain covered. Phase10F.2 subsequently built FINAL111: 326 regression, 17 wizard, 932 differential, 161 frozen and 201 packaging checks passed. These are historical build-time results; Phase10G results are recorded separately. v1.1.1 is published and manually tested by owner report; independent recovery/DPI/stock-Windows coverage remains incomplete.
