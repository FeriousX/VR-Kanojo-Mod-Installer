# Build instructions

Current maintenance source: **v1.1.1**, target **FINAL111**, numeric version **1.1.1.0**. Configuration: [final-v1.1.1.json](../manifests/final-v1.1.1.json). [v1.0.0](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases/tag/v1.0.0) and [v1.1.0](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases/tag/v1.1.0) are published; their assets and historical recipes are preserved. Current artifact identities remain in [RELEASE_ARTIFACTS.json](RELEASE_ARTIFACTS.json); next-source status is [RELEASE_PREPARATION.json](RELEASE_PREPARATION.json).

Use the previously qualified official CPython 3.14.10 x64 archive (SHA-256 90905E64A840557D8C1BC4F5B74DB3D7EE85E3FFB217611CAC1C7813ACEA4159), hash-pinned build-requirements wheels including PyInstaller 6.22.3, signed Inno Setup 7.1.1, and exact verified component/notice inputs. No dependency upgrades. Native gate requires exactly 18 approved DLL/PYD files with no extras; isolated build search paths remain enforced.

Source checkout intentionally excludes runtime/plugin binaries and toolchain caches. Stage the exact reviewed payload under payload/<staged_source> in a separate build workspace. Maximum profile remains 56 files and four independent default-off utilities. Phase10E measured 109 embedded inputs (107 backend files plus resource manifest/recovery helper); derive actual counts/bundle from a new build, do not assume them.

In a separately authorized build phase, with verified explicit local inputs:

```powershell
& $PythonExe -I -B tools/source_export_plan.py
& $PythonExe -I -B tools/prepare_final110_notices.py --destination out/final111-notices
& $PythonExe -I -B tools/build_single_exe.py --milestone FINAL111 --python $PythonExe --runtime-archive $OfficialPythonZip --runtime-provenance docs/RUNTIME_PROVENANCE_8C3.json --notices out/final111-notices
& tools/compile_single_exe.ps1 -Kind FINAL111 -CompilerPath $QualifiedISCC
```

Notice helper's historical filename is retained; its exact cleared notice behavior is unchanged. Outputs: out/FINAL111, build/FINAL111, out/final-v1.1.1 and out/FinalRelease_v1.1.1/VRK-Mod-Installer-v1.1.1.exe. Compiler hash/signature/version, explicit runtime/notices/catalog pins and artifact overwrite refusals remain required.

After an actual verified build and intentional source-pin review, the existing source packager supports `python -B tools/package_source110.py --release-version 1.1.1`, producing VRK-Mod-Installer-v1.1.1-Source.zip in the separate version directory. Its historical filename is retained to avoid unrelated relocation. This command creates an archive; it is not run in commit preparation. No EXE/ZIP was generated in Phase10F.1.

The v1.1.0 recipe remains in final-v1.1.0.json. Explicit `--milestone FINAL110`, `-Kind FINAL110`, and `--release-version 1.1.0` retain separate output paths and macro definitions. Existing released outputs must never be overwritten. Read-only `load_final_config(root, '1.1.0')` validates that historical recipe; default selection is 1.1.1. Source-export validation checks the current development tree, not the immutable published v1.1.0 source ZIP.

All moved modules and legacy aliases must be present in a future frozen build. Use [testing](TESTING.md) and [source provenance](SOURCE_PROVENANCE.md). A source-validated recipe is not a proven v1.1.1 executable; verify runtime/native/payload/resource/license integrity and version metadata in the next authorized build. No bit-identical, clean-Windows or universal DPI guarantee is claimed. Persistent runtime/transaction paths and formats remain unchanged.
