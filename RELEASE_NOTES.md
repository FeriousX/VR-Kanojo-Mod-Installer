# Release notes

## v1.1.1 maintenance changes

This maintenance source carries the Phase10 documentation/navigation corrections and the two targeted runtime transport moves, with compatibility imports preserved. Existing component versions/selections, installer behavior, consent, hashes, backups and recovery formats are unchanged. See [architecture](docs/ARCHITECTURE.md), [build guide](docs/BUILDING.md) and [preparation record](docs/RELEASE_PREPARATION.json).

The owner reports successful Phase10E local-test installation and gameplay in original VR Kanojo v1.31. This evidence applies to that exact local test (11,135,199 bytes; SHA-256 9409B0299E0F75A7A9952B456A47ED0B8BE0C8ACD2A53E92F9613ACEF86F0620), not a newly built v1.1.1 installer. Manual recovery retest, extra DPI and stock Windows remain unverified; unsigned status remains.

Use the [official releases](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases) for actual published downloads. Source preparation is not publication.

## v1.1.0 — published November 7, 2026


Maintained by FeriousX for original VR Kanojo (2018), owner-tested with v1.31. VR-Kanojo (2025) is unsupported. Independent modernization of ManlyMarco's HF Patch lineage; not a game repair/update or complete historical HF Patch replacement.

Included in v1.1.0: four exact cleared optional mods, independently selectable and off by default:

| Optional component | Version | License | Default |
|---|---|---|---|
| Message Center | 1.1.1 | GPL-3.0 | Off |
| Mute In Background | 1.1 | GPL-3.0 | Off |
| FPS Counter | 3.1 | Apache-2.0 AND zlib | Off |
| Graphics Settings (official) | 1.2.1 | GPL-3.0 | Off |

BepInEx 5.4.12 x64, required dependencies and optional FeriousX Desktop 1.0.4 are retained. Component descriptions now live in a bounded native scrolling list, clear of the footer. Exact-plan consent, validation, ownership, backup and persistent recovery behavior are unchanged.

Selected optional mods carry their exact licensing notices/source materials. Mute needs its native setting enabled after installation; Graphics supports the documented startup config values, without an advanced menu. No original Play Without VR, XUnity/Uncensor Loader, compiler/developer plugins or legacy Configuration Manager. No repair assets, model collections or replacement saves.

Owner reports core installation/gameplay, all four optional mods and footer fix passed. Recovery retest, additional DPI and stock Windows remain NOT VERIFIED; previous confirmed environment is Windows X-Lite Optimum (modified Windows 11 Pro x64). Unsigned; no universal compatibility or guaranteed power-loss/hostile-race recovery claim. No separately installed Python is needed by the bundled implementation.

Published as a full [v1.1.0 GitHub Release](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases/tag/v1.1.0) on November 7, 2026 (18:10:54 UTC). The published EXE and corresponding-source ZIP match the measured Phase9E3 identities; see [artifact metadata](docs/RELEASE_ARTIFACTS.json).

Publication is verified separately from testing. Historical packaging evidence remains in [Phase9E3 verification](docs/V1.1.0_PACKAGE_VERIFICATION.md); it records observations at build time, not current publication status. This documentation update performed no new installer, gameplay or independent recovery/DPI/stock-Windows tests.
