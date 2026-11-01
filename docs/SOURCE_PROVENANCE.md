# Source provenance

This is a source-only Phase 8D export, with no Git repository initialized and no Git operations performed. It retains the actual application/backend/wizard implementation used for the Phase 8C.3A RC. Source-to-build-input checks compare those files against the retained packaging snapshot; the RC hash and embedded-resource inventory are recorded separately. Documentation/build-helper updates are not represented as a reproducible compiler rebuild.

Original lineage: [ManlyMarco VR Kanojo HF Patch](https://github.com/ManlyMarco/VRK-HF_Patch), v1.1-era GPL source and retained author notices. The modernization reuses that lineage but not its historical game asset/helper binaries or destructive installation routines. FeriousX maintains the new installer and Desktop plugin.

Desktop source is the previously captured publisher-associated commit `a4e49c3e01c2d98b68d9ecab36dba7e3246688dd`; its project/build files, GPL notice and editable crosshair source are in third_party/source. Independent reproducible compilation of that plugin is not claimed.

The essential framework association and current official Python runtime provenance/notice requirements were cleared in the existing audit; this milestone does not reopen them. The old development 3.12.14 runtime was replaced, not approved. Current records are `ESSENTIAL_PROVENANCE.json`, `RUNTIME_PROVENANCE_8C3.json`, `RUNTIME_SIGNATURES_8C3.json`, `RUNTIME_3_14_10_NOTICE_EVIDENCE.json`, `license-audit.csv` and `EMBEDDED_FILE_INVENTORY.json`.

Excluded from this export: old private review reports, obsolete runtime-reference files, binary payloads/toolchains, game assets and paths, archives, logs, live journals/backups/receipts, DPAPI state and credentials, Git internals and developer output. Only specifically GPL-licensed Desktop crosshair source assets remain. Historical evidence is preserved in the maintainer workspace, not deleted by this export.

The source SHA-256 manifest is generated after documentation preparation. Line-ending normalization or later changes require a new manifest and source archive. Exact binary and source hashes are separate; neither proves clean-Windows compatibility.
