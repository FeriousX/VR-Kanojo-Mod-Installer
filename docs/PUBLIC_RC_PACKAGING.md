# Public RC v1.0.0-rc.1 packaging

## Result

Prepared locally for the owner's public **pre-release** review/publication. No Git command, tag, upload, remote change or publication was performed. This is not a stable v1.0.0 release or universal Windows qualification.

The packaging uses the cleared official CPython 3.14.10 x64 runtime and PyInstaller 6.22.3 frozen backend. It was compiled with the qualified official Inno Setup 7.1.1 x64 compiler. The frozen backend was deliberately reused, not rebuilt: all 80 embedded resource bytes and the persistent bundle identifier remain identical to the approved base. All 27 physical component files match the approved reduced manifest; nine excluded optional groups remain physically absent.

## Changes

- Product/AppVersion `1.0.0-rc.1`, numeric Windows file version `1.0.0.1`, maintainer FeriousX, public pre-release description and filename.
- Public release footer and neutral installation error labels replace obsolete Private wording in the current wizard branch.
- Complete license text, bounded scrollable acceptance dialog, default Decline and silent-mode refusal remain exactly unchanged.
- No backend/transport code, protocols, state identity, path/ownership checks, plan consent, backup/recovery, plugin DLLs or seven-page design changed.
- Corresponding source includes explicit RC1 packaging targets, exact runtime/notice information and current release documentation. Internal legacy identifiers remain for state/protocol compatibility, not copy-specific restrictions.

## New focused checks

20 packaging/safety checks passed, zero failures. They verify the exact approved source baseline; Pascal code differs only in four allowed visible strings; complete license-dialog code identical; backend/transport source unchanged; all 80 resources rehash; source/runtime catalog equality; only approved groups and 27 physical files; general technical target policy; unchanged persistent bundle; real PE product/company/version/description; silent refusal without acceptance; frozen 3.14.10 backend startup with invalid external Python paths and Windows-only PATH; exact notices/source preserved; source version alignment. Inno compile completed successfully without reported errors/warnings. Padding spaces in Inno's PE version strings are normalized for comparison.

These are packaging/safety checks, not a repeated gameplay or real-game installation test. Earlier installation/consent/recovery tests and the owner's manual approval are reused because the underlying bytes and functionality are unchanged. No user's game was accessed or launched. The complete artifact has not been manually gameplay-tested again after metadata changes.

Additional final documentation/export checks verify local links, syntax, source-only privacy/file types, exact checksums and source ZIP/tree equality. Their result is recorded in the external packaging report, not inferred from compiler success.

## Limits and owner action

No unresolved essential license/source/integrity failure was waived. This RC is unsigned. Confirmed base environment: Windows X-Lite Optimum (modified Windows 11 Pro x64), fresh install/reinstall/game/Desktop controls, no external Python. Other Windows configurations, clean stock Windows 10/11 and the full six-setting interactive DPI matrix remain NOT VERIFIED. Prior geometry/available-desktop tests are not presented as full display qualification.

The owner should review checksums, notes/source and the public labels, then mark the GitHub release as a pre-release with tag `v1.0.0-rc.1`. Clean-Windows qualification remains recommended before a stable release. No final stable filename is produced, and the project does not promise a new mod menu or dates.
