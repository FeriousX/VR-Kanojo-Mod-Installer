# Architecture and source layout

This describes the current maintenance-source implementation, not a proposed reorganization. Phase10D1 relocated presentation; Phase10D2 relocates only the stdin/stdout selection CLI. Other runtime and engine paths remain unchanged. Start with the [documentation index](README.md), [build guide](BUILDING.md) and [test guide](TESTING.md).

## Main path

```text
Inno wizard: src/installer/ui-prototype/preview.iss
  -> verified bundled HFBackend.exe, private-gui prepare/run/recover
  -> tools/portable_backend.py -> tools/private_gui_install.py
  -> tools/gui_install.py (job frames, progress and worker lifecycle)
  -> src/hf_payload/private_game_bridge.py
  -> external target checks + component planning + consent
  -> registry / coordinator / journal / apply and recovery
```

Despite the inherited ui-prototype/private/synthetic names, this route supports compatible original-game targets. Those names are not authorization checks: explicit target validation, exact-plan consent, ownership and hash verification remain required. Historical CLI/status identifiers also support recovery and should not be renamed casually.

## Where to find things

| Area | Current location and role |
| --- | --- |
| Wizard and persistent resource verification | [preview.iss](../src/installer/ui-prototype/preview.iss), [embedded_cache.iss](../src/installer/ui-prototype/embedded_cache.iss) |
| Runtime entry and GUI transport | [portable_backend.py](../tools/portable_backend.py), [private_gui_install.py](../tools/private_gui_install.py), [gui_install.py](../tools/gui_install.py), [transport/presentation.py](../src/hf_payload/transport/presentation.py); the old [gui_presentation.py](../tools/gui_presentation.py) is only a compatibility import. Other runtime code still shares tools with build scripts |
| Target detection and compatibility | [detection.py](../src/hf_payload/detection.py), [game_compatibility.py](../src/hf_payload/game_compatibility.py), [external_root.py](../src/hf_payload/external_root.py), [private_target.py](../src/hf_payload/private_target.py) |
| Components and release scope | [real_components.py](../src/hf_payload/real_components.py), [component_packages.py](../src/hf_payload/component_packages.py), [catalog](../manifests/real-components.json), [scope](../manifests/release-scope.json) |
| Plan, ownership and consent | [planner.py](../src/hf_payload/planner.py), [ownership.py](../src/hf_payload/ownership.py), [registry.py](../src/hf_payload/registry.py) |
| Execution and recovery | [coordinator.py](../src/hf_payload/coordinator.py), [recovery.py](../src/hf_payload/recovery.py), [external_root.py](../src/hf_payload/external_root.py); recovery.py also holds shared safe I/O and journal helpers |
| Persistent paths and credentials | [runtime_paths.py](../src/hf_payload/runtime_paths.py), [private_credentials.py](../src/hf_payload/private_credentials.py); per-user DPAPI and retained recovery state |
| Build, runtime qualification, source export | [build_single_exe.py](../tools/build_single_exe.py), [compile_single_exe.ps1](../tools/compile_single_exe.ps1), [release_config.py](../tools/release_config.py), [source-export rules](../manifests/source-export-rules.json) |
| Tests and vendored material | [tests](../tests), [third_party](../third_party), [notices](../THIRD_PARTY_NOTICES.md) |

The wizard polls bounded job response frames. Preparation validates a plan; execution requires separate explicit consent. Backend completion is reported only from its verified transaction result. Synthetic commands (gui/install/validate) and the real-gui component-fixture route remain qualification tools; they do not share the same target authority as private-gui.

## Boundaries to preserve

Keep GUI presentation separate from target/file authority. Preserve component identities, canonical transaction/receipt/journal formats, consent replay/expiry checks, exact-type area checks and DPAPI account scope. Persistent state lives outside temporary extraction under `%LOCALAPPDATA%\FeriousX\VRKMI`; old transactions need their matching retained runtime. See [recovery](RECOVERY.md).

Future cleanup can separate runtime scripts from tools, replace temporary module-global mode switching, organize Inno includes and extract shared recovery primitives. These are future code changes requiring regression and development-build qualification; this guide does not claim they have happened.

## First incremental transport separation (Phase10D1)

Only `tools/gui_presentation.py` implementation moved to `src/hf_payload/transport/presentation.py`, byte-for-byte. Current GUI transport and tests import the canonical package. The old tools path remains a minimal forwarding module because external/source callers may still import it; it re-exports the same function and shared objects. In frozen mode it never adds a development source path. The existing builder already searches src and follows the canonical static import. One explicit hidden-import entry retains the legacy forwarding module in future frozen bundles, even though current callers use the new package.

No CLI, result fields, state strings, consent, transaction formats, resource locations or GUI behavior changed. Source/import/static/synthetic regression checks are distinct from actual frozen-runtime qualification. No installer is built in this phase; a later authorized development freeze and GUI smoke test remains required before distributing the reorganized runtime.

## Selection adapter separation (Phase10D2)

The original `tools/validate_ui_selection.py` stdin/stdout adapter now lives in [transport/selection_cli.py](../src/hf_payload/transport/selection_cli.py). Its `main()` implementation, JSON bounds/duplicate-key/nonfinite handling, fixture validation and return codes are unchanged. Only script-relative source-path setup was removed from the canonical module; state remains resolved by the unchanged backend.

The [old script](../tools/validate_ui_selection.py) forwards execution and aliases imports to the canonical module, preserving exported objects and monkeypatch behavior. The [dispatcher](../tools/portable_backend.py) uses the canonical import while retaining its existing validate command. A single explicit freezer collection entry retains the old compatibility module; no frozen build was produced. This adapter only validates synthetic selection proposals and does not gain real-game target or execution authority.

Source/differential/import tests and frozen-layout simulation are not an actual PyInstaller/GUI qualification. Published installers and historical recovery bundles remain unchanged; an authorized development build is still needed before distributing reorganized code.

## Tested maintenance baseline and version preparation

Phase10E built this approved runtime reorganization as an isolated local test; the owner subsequently confirmed installation and gameplay on original VR Kanojo v1.31. [Preparation metadata](RELEASE_PREPARATION.json) records that exact artifact and remaining gaps. Phase10F.1 prepares source labels/build configuration for v1.1.1 without another runtime move or behavior change. Phase10F.2 subsequently built and locally verified v1.1.1, now published and manually tested by owner report. Historical source and runtime recovery mappings remain unchanged; post-release metadata edits are not part of the immutable published source ZIP.
