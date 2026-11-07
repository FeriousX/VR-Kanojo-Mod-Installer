# v1.1.0 build configuration — candidate recipe

Use the dedicated **FINAL110** target in manifests/final-v1.1.0.json. Do not use FINAL100 for this release. Phase9E2 prepared this route; Phase9E3 executes it for the local candidate. AppVersion is 1.1.0 and numeric version 1.1.0.0; previous dev.3 remains unchanged.

Qualified inputs: official CPython 3.14.10 Windows x64 archive (SHA-256 90905E64A840557D8C1BC4F5B74DB3D7EE85E3FFB217611CAC1C7813ACEA4159), pinned build-requirements.txt wheels including PyInstaller 6.22.3, signed Inno Setup 7.1.1 x64, exact reviewed payload and preserved notices. No runtime/plugin upgrades. The native gate must match all 18 official DLL/PYD files with no extras. Build environment isolation remains in runtime_build_env.py; no development PATH/native DLL fallback.

The maximum component profile is **56 files**, seven approved groups: framework, loader settings, Desktop and four default-off utilities. Restore verified payload bytes separately under payload/<staged_source>; none is taken from the game by the build. Current reference has **107 resource inputs**; final resources/count/bundle must be derived from the actual FINAL110 output, not assumed identical.

Rebuild commands, only in an authorized build phase (replace input paths with separately verified local inputs):

```powershell
& $ExistingPython -B tools/prepare_official_runtime.py --archive $OfficialPythonZip --wheels $PinnedWheels --destination cache/qualified-python
$PythonExe = (Resolve-Path cache/qualified-python/python.exe).Path
& $PythonExe -I -B tools/source_export_plan.py
& $PythonExe -I -B tools/prepare_final110_notices.py --destination out/final110-notice-inputs
& $PythonExe -I -B tools/build_single_exe.py --milestone FINAL110 --python $PythonExe --runtime-archive $OfficialPythonZip --runtime-provenance docs/RUNTIME_PROVENANCE_8C3.json --notices out/final110-notice-inputs
& tools/compile_single_exe.ps1 -Kind FINAL110 -CompilerPath $QualifiedISCC
```

Notice staging refuses an existing destination. Source-plan validation is read-only and does not create a ZIP. FINAL110 requires explicit qualified runtime/notices inputs and a fresh isolated output. Compiler wrapper checks its pinned hash, version and signature, prepared configuration and output overwrite protection. Preserve old artifacts; do not use a final label for dev.3 bytes.

Outputs: intermediate bundle out/FINAL110, generated script build/FINAL110/single.iss, logs out/final-v1.1.0, intended EXE out/FinalRelease_v1.1.0/VRK-Mod-Installer-v1.1.0.exe. Matching source ZIP is VRK-Mod-Installer-v1.1.0-Source.zip. After recording/reviewing actual EXE metadata and any intentionally changed source pins, tools/package_source110.py creates the source-only archive and refuses existing output. Its own identity belongs in the external release record, not inside itself. Validate the final resource manifest, source correspondence, licenses, artifact hashes and metadata before publication. No bit-identical rebuild or clean-Windows guarantee is claimed.

The clean export rules are manifests/source-export-rules.json: explicit file list/hashes, no runtime binaries/private state, only reviewed corresponding-source archives. Include a newly generated SOURCE_SHA256SUMS.txt for the actual exported tree. Developer payloads/toolchains remain separate inputs. Never zip the whole workspace.

Application identifiers, plugin GUIDs, protocol/transaction formats, persistent storage and recovery behavior remain unchanged. See SOURCE_PROVENANCE.md, DISTRIBUTION_AUDIT.md and RELEASE_READINESS.md for evidence/limits. Historical build reports are records, not current commands.
