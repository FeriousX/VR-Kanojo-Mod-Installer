# Corresponding source and build information

Official unmodified source snapshot: `BepInEx.Utility-f1a40ffe37be96e6710df6029c26255d1a0a5393-Source.zip`.

- Publisher URL: https://codeload.github.com/BepInEx/BepInEx.Utility/zip/f1a40ffe37be96e6710df6029c26255d1a0a5393
- Commit: `f1a40ffe37be96e6710df6029c26255d1a0a5393` (Utility r7).
- Size: 51716 bytes.
- SHA-256: `0BC7931EFEFC7233983635CB9F584618E292B090DEEC11D04CB69BDED83393A5`.
- Full source archive is included under official-archives, with GPL, README, solution, all selected C# sources/project files and release.ps1. It contains no compiled DLL/EXE. No archive contents were executed or built.

The two selected projects target .NET Framework 3.5, with System/.NET references and external `lib/BepInEx.dll` / `lib/UnityEngine.dll` build references. The upstream C# language/toolchain requirements and release.ps1 remain preserved. No compiler or proprietary SDK is supplied by this report. Any future rebuild needs a legitimate local Unity/game reference and matching BepInEx reference; do not download unofficial game DLLs or include them in the redistributable source/payload. This review does not assert that a rebuild was completed or byte-for-byte reproduction is available.

The selected projects have no source-submodule, NuGet package or ILRepack/merged-compiler requirement in their reviewed project files; their Compile lists directly cover the supplied selected project C# files. Framework libraries are separate existing prerequisites. Message Center includes its own LogEntry/LogListener/ShadowAndOutline helper source; no different helper/asset license or externally supplied image is declared in those inspected files. No separately licensed models or other optional plugin binaries are included in the two official runtime ZIPs.

Tag ambiguity: r5 to r7 changes **no selected C# source or root LICENSE**. The two csproj differences only change OutputPath from bin to bin/BepInEx/plugins. This strengthens the r7 publisher-source association but does not claim a unique original build date/compiler or a reproducible build. The precise origin asserted here is that these exact retained bytes are offered by the official r7 release, with its tagged source. Different future r8/r9 packages are outside clearance.

For a future GPL online binary release, place the exact source archive and notice files at equivalent downloadable access alongside the binaries (GPLv3 section 6(d)), preserve original notices, and document all actual changes. Do not bundle these optional mods into v1.0.0 or alter the installer as part of this review.
