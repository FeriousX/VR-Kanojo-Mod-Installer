# Source correspondence

Current v1.1.1 maintenance source retains the published v1.1.0 engine/payload behavior with the documented Phase10 transport relocations, documentation and version metadata changes. It is not byte-identical to the immutable published v1.1.0 source ZIP. Dev.3 remains the preserved owner-tested development reference. Source archive SHA-256 and size are external records, since a ZIP cannot contain its own identity without circularity. Phase9E1 verified 181 indexed inputs, 56 staged files, 107 packaged resource inputs and an identical qualified backend. Release preparation changes docs/build configuration and metadata, not installation engine or plugin bytes.

The final source must include exact application/backend/wizard/build modifications, GPL project/upstream notices, Desktop 1.0.4 preferred source/resources/build information and individual optional-plugin source/notices. Optional provenance: Utility r7 f1a40ffe37be96e6710df6029c26255d1a0a5393 (Message Center/Mute), FPS dc2884a3778a4785e1ffa8e3b0b0940f3dde786c, Graphics b161594317cae4caa83eb82a59076e961c0ab004. Graphics preferred-source ZIP was locally assembled from ten exact tagged blobs, not an official upstream-built archive. No independent byte-identical plugin rebuild is claimed.

Use the explicit allowlisted source-export rules and read-only validation. Runtime/payload binaries, official binary plugin ZIPs, game assets, toolchains, out/build/cache, historical private investigations, logs, journals/backups/receipts and DPAPI credentials are not source-export inputs. Only GPL Desktop crosshair source and reviewed corresponding-source ZIPs are retained where applicable. License evidence JSON is not permission to ship unrelated SDK/game files.

After any input change, re-review and refresh the source rules/hashes intentionally. Generate the final source inventory from the actual exported tree, not this private workspace's inventory. Hashing establishes correspondence/integrity, not authenticated ownership or Windows compatibility.

Existing essential/native provenance and exact notices remain authoritative: ESSENTIAL_PROVENANCE.json, RUNTIME_PROVENANCE_8C3.json, RUNTIME_SIGNATURES_8C3.json and RUNTIME_3_14_10_NOTICE_EVIDENCE.json. Complete published EXE/source/checksum identities are in [RELEASE_ARTIFACTS.json](RELEASE_ARTIFACTS.json). Historical package records remain unchanged.

## Post-release documentation boundary

Phase10C changed documentation/publication metadata; Phase10C1 aligns the active development source-export pins and release tests. Neither phase rebuilds or replaces published artifacts. The active `manifests/source-export-rules.json` describes the reviewed post-release development source, explicitly separate from the immutable published v1.1.0/v1.1.1 ZIPs.

The root `SOURCE_SHA256SUMS.txt` remains the historical pre-cleanup inventory, not a checksum list for current documentation. Published v1.0.0/v1.1.0/v1.1.1 archives and their embedded inventories/checksums remain untouched. Use the read-only `tools/source_export_plan.py` to validate the active list; it does not export files or create a ZIP. A future source package needs its own source revision/inventory and must not overwrite the published archive.

Release tests distinguish current PUBLISHED metadata, historical unpublished candidate/development identities and the immutable FINAL110 build-time recipe. All path/hash/archive-provenance exclusions remain enforced. See [test guide](TESTING.md).

Phase10F.1 prepares v1.1.1 source/build metadata only, after owner-reported installation/gameplay success with the exact Phase10E local test. The active export list is explicitly marked as v1.1.1 development source and includes both relocated modules and compatibility imports. Historical root SOURCE_SHA256SUMS.txt, v1.0.0/v1.1.0 source inventories and released archives remain unchanged; a current development checksum plan is saved in the external commit-preparation report directory. No new source archive is generated here.

## Published v1.1.1 boundary

Phase10F.2 generated the exact published EXE and corresponding-source ZIP from 185 reviewed inputs plus its generated checksum inventory. Phase10G updates only current documentation/metadata, directly affected tests and active export pins. These post-release bytes must not be represented as the contents of the published ZIP. Its historical embedded inventory, tag commit and complete archive identity remain immutable. v1.1.1 is published and owner-tested; no new package is generated here. Source/build recipes retain their original `published: false` build-time constraint, not a current publication declaration.
