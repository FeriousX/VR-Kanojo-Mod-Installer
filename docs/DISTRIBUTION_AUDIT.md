# v1.1.0 distribution scope

Candidate scope: BepInEx 5.4.12 x64/loader settings, optional FeriousX Desktop 1.0.4 or neither, and four independently optional/default-off utilities. Maximum is **56 mapped files**. The actual FINAL110 candidate input inventory has **107 resource inputs**, including 18 official native DLL/PYD dependencies. These counts were measured from the actual FINAL110 build resources; no independent extraction of the final Inno EXE is claimed.

| Optional component | Version | License | Default |
|---|---|---|---|
| Message Center | 1.1.1 | GPL-3.0 | Off |
| Mute In Background | 1.1 | GPL-3.0 | Off |
| FPS Counter | 3.1 | Apache-2.0 AND zlib | Off |
| Graphics Settings (official) | 1.2.1 | GPL-3.0 | Off |

Exact DLL hashes/source commits and original notices are retained in the component catalog, optional component source/notice trees and license audit. Selected installation includes GPL/source obligations for Utility/Graphics and Apache-2.0/Gavin Pugh zlib materials for FPS. Project GPL does not replace these or Python/native/Microsoft terms. Preserve core MIT/Harmony/MonoMod/Cecil, historical Doorstop CC0, project/Desktop GPL, PSF/incorporated-library and PyInstaller notices separately.

Excluded: Original Play Without VR, XUnity Common/Resource Redirector, Uncensor Loader, Runtime Unity Editor, Script Loader and Configuration Manager; repair/update payloads, uncensor collections, replacement saves and obsolete unrelated files. Actual catalog/runtime payload, not just GUI visibility, enforces scope. No conditional/blocked component is restored by documentation.

Official CPython 3.14.10 x64 + PyInstaller 6.22.3 are unchanged. Native provenance still requires exactly 18 approved native files; no development-collected UCRT/API-set DLLs. The final build needs explicit qualified runtime archive, native provenance and notices. Phase9E3 ran these gates; see the external final verification record.

The candidate is locally built and unpublished. EXE identity is recorded here; ZIP identity is recorded externally beside the archive. Public source uses explicit clean export rules; private recovery data and game/payload binaries are excluded. Owner-reported passes are separate from unverified recovery retest, additional DPI and stock Windows. Unsigned status remains. See RELEASE_ARTIFACTS.json, EMBEDDED_FILE_INVENTORY.json, SOURCE_PROVENANCE.md and RELEASE_READINESS.md.
