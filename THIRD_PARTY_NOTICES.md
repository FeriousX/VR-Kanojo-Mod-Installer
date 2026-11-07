# v1.1.0 optional component notices

| Optional component | Version | License | Default |
|---|---|---|---|
| Message Center | 1.1.1 | GPL-3.0 | Off |
| Mute In Background | 1.1 | GPL-3.0 | Off |
| FPS Counter | 3.1 | Apache-2.0 AND zlib | Off |
| Graphics Settings (official) | 1.2.1 | GPL-3.0 | Off |

Utility r7 Message Center/Mute: preserve exact GPLv3, original attribution and complete corresponding source under third_party/Utility-r7. FPS: preserve Apache-2.0 and Gavin Pugh 2010 zlib helper notices/terms, source and attribution under third_party/FPSCounter-v3.1. Official Graphics: preserve GPLv3 and the preferred tagged source/build materials, attribution and source information under third_party/GraphicsSettings-v1.2.1. Selected installation carries these under HF_Patch_Notices. All four DLLs are unmodified; other historical variants are not covered by these approvals. All four are off by default.

# Third-party notices

This project is independently maintained by FeriousX from ManlyMarco's GPL-licensed installer lineage. Project GPL terms do not replace individual bundled-component licenses.

| Distributed component | Version / terms | Preserved materials |
| --- | --- | --- |
| BepInEx and managed dependencies | 5.4.12; HarmonyX 2.5.1; MonoMod 21.7.8.3; Cecil 0.10.4; pinned compatibility shim, MIT | `third_party/licenses/essential` and exact source/binary association in `docs/ESSENTIAL_PROVENANCE.json` |
| Unity Doorstop | Historical 3.4.0.0, CC0-1.0 | Exact historical notice in essential; modern Doorstop terms are not substituted |
| VR Kanojo Desktop | 1.0.4, GPL | `third_party/source/VRKanojoDesktop-v1.0.4`, its license/build/project/crosshair sources and embedded source archive |
| CPython / incorporated libraries | Official 3.14.10 Windows build; PSF/historical and separate incorporated terms | `third_party/licenses/runtime-3.14.10`; official SBOM, exact runtime file hashes and upstream notice references |
| OpenSSL / libffi / bzip2 / liblzma / mpdecimal / zlib-ng / zstd / HACL* | Exact versions in the runtime provenance inventory | Individual preserved notices; no blanket PSF or GPL substitution |
| Microsoft runtime code | VC 14.51.36247.0 from the official Python archive; OS UCRT not bundled | Official Windows Python Additional Conditions, presented for acceptance before backend startup; apply only to Microsoft Distributable Code |
| PyInstaller | 6.22.3; COPYING with bundling/bootloader exception and applicable Apache terms | `third_party/licenses/essential/PyInstaller-6.22.3-COPYING.txt` |
| Inno Setup | 7.1.1 | `third_party/licenses/Inno-Setup-LICENSE.txt` |

Exact notice texts remain unmodified. Current embedded resources are listed in [inventory](docs/EMBEDDED_FILE_INVENTORY.json); [license audit](docs/license-audit.csv) separates CLEARED from EXCLUDED groups. A repository or credit link is not automatic redistribution permission. Some historical author attributions remain for lineage even though their plugin binaries are excluded.

No Configuration Manager, conditional/blocked optional groups, game assets, repair files or replacement saves are embedded. Preserved historical VRKanojo plugin license text is a reference/attribution, not a claim that all of those plugins are bundled.

Publish equivalent access to the exact corresponding project/Desktop source and build instructions alongside any binary release. Preserve upstream copyrights, GPL and individual notices. No public release is created by this preparation.
