# Build instructions and source relationship

The current release is v1.0.0. It reuses the exact cleared Phase 8C.3A frozen backend/resources; the Inno packaging layer was rebuilt with release metadata and wording only. Its application/backend/wizard/build source is provided in this tree. No backend or installation behavior was changed. Source checksums and artifact hashes are supplied; bit-for-bit rebuilds are not claimed because build timestamps and packaging metadata can vary.

## Qualified inputs

- Official Inno Setup **7.1.1 x64**. The compiler hash/signature/version are checked by `tools/compile_single_exe.ps1`; expected portable path: `cache/inno-7.1.1-x64/portable`.
- Official PSF **Python 3.14.10 Windows x64 embedded archive** from https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip . Expected SHA-256: `90905E64A840557D8C1BC4F5B74DB3D7EE85E3FFB217611CAC1C7813ACEA4159`.
- The seven wheel hashes in `build-requirements.txt`, including **PyInstaller 6.22.3**. They are build-only dependencies; end users install none of them.
- The 27 approved payload mappings in `manifests/real-components.json` (22 without Desktop), with exact sizes/hashes and official component provenance. Restore these under `payload/<staged_source>` only after verifying them. Do not restore excluded optional runtime files. Required payload binaries are intentionally not included in this source tree.

The BepInEx release source is https://github.com/BepInEx/BepInEx/releases/tag/v5.4.12 ; its official x64 archive is recorded in the component lockfile. Desktop 1.0.4's recorded publisher binary/source association and source commit are preserved in the component catalog and `third_party/source/VRKanojoDesktop-v1.0.4`. Authored loader settings are supplied under `templates`; their bytes must match the mapped payload. Do not replace game assemblies, invent missing files, or relax a hash mismatch.

## Rebuild process

Use an existing trusted Python only to prepare the isolated build environment. This is not an end-user dependency. Obtain inputs from their official sources and retain their licenses first.

```powershell
& $ExistingPython -B tools/prepare_official_runtime.py --archive cache/python-3.14.10-embed-amd64.zip --wheels cache/pyinstaller-6.22.3-wheels --destination cache/qualified-python
$PythonExe = (Resolve-Path cache/qualified-python/python.exe).Path
& $PythonExe -I -B tools/prepare_notice_inputs.py
& $PythonExe -I -B tools/build_single_exe.py --milestone FINAL100 --python $PythonExe
& tools/compile_single_exe.ps1 -Kind FINAL100
```

The preparation helper verifies the official archive and pinned wheel hashes, verifies PSF signatures and creates only an application-local build environment. It does not install Python system-wide or alter system PATH. Stock Windows PowerShell Security is imported by explicit path for signature verification. The build uses an explicit qualified interpreter and must exclude unrelated development-native DLL search paths; use Windows System32/Windows only in the build process's PATH and remove inherited PYTHONHOME/PYTHONPATH. The builder refuses existing output directories rather than overwriting evidence. `prepare_notice_inputs.py` likewise requires a fresh notice-input directory.

The FINAL100 target emits `out/FinalRelease_v1.0.0/VRK-Mod-Installer-v1.0.0.exe`, AppVersion/ProductVersion `1.0.0` and numeric Windows file version `1.0.0.0`. Final product/release title is VR Kanojo Mod Installer v1.0.0; the owner's tag is `v1.0.0`.

The recorded final packaging reused all 80 cleared backend/resource bytes and rebuilt only the Inno layer with final version and wording. A complete from-source build uses the commands above and independently qualifies its resulting bytes; timestamp-dependent output is not claimed identical. Internal legacy preprocessor flags, CLI/profile names and persistent state identifiers stay unchanged to preserve compatibility; they do not impose individual-copy enrollment. Do not rename those identifiers or transaction formats merely for branding.

The wizard must embed the entire prepared backend, current notices and approved payload; do not ship or rely on a user-managed sidecar runtime. Persistent transaction state stays at `%LOCALAPPDATA%\FeriousX\VRKMI`, never in the temporary build/extraction directory.

## Tests and limits

`tools/run_source_tests.py` runs a selected synthetic source subset with a qualified interpreter. Historical integration fixtures and live game evidence are intentionally not shipped. Phase 8D performs source/artifact/document checks without rerunning the historical regression suites or gameplay. See [readiness](RELEASE_READINESS.md), [distribution audit](DISTRIBUTION_AUDIT.md) and [clean Windows procedure](CLEAN_WINDOWS_TESTING.md). Synthetic trust keys are never production credentials.
