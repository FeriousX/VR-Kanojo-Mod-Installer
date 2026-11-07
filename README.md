# VR Kanojo Mod Installer

Maintained by **FeriousX** | [Repository](https://github.com/FeriousX/VR-Kanojo-Mod-Installer)

A self-contained Windows installer for the plugin framework and optional desktop controls in **original VR Kanojo (2018)**. Independently maintained and based on ManlyMarco's GPL-licensed VR Kanojo HF Patch installer. This is not an official game update or a complete replacement for every feature in the historical HF Patch.

Download the current installer and matching source from the **[official releases](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases)**. [Publication records](docs/RELEASE_ARTIFACTS.json) preserve verified artifact identities; publication and testing qualification are separate.

The owner reports core installation/gameplay, all four optional mods and the Components-page footer correction working. Recovery retest, additional DPI settings and clean stock Windows are **NOT VERIFIED**. Earlier confirmed testing used Windows X-Lite Optimum (modified Windows 11 Pro x64); other Windows configurations are not independently qualified. The installer is **unsigned** and uses a bundled runtime, with no separately installed Python required. See [release readiness](docs/RELEASE_READINESS.md).

## What it installs

- **BepInEx 5.4.12 x64**, including its required loader and managed dependencies.
- Game-specific loader entry-point settings, with existing-file/configuration safeguards.
- Optional **VR Kanojo Desktop v1.0.4 by FeriousX**, or **neither** to keep a VR-oriented setup. Desktop provides mouse/keyboard controls, reliable mouse capture and up to 6 meters of virtual-hand reach. See its [control documentation](third_party/source/VRKanojoDesktop-v1.0.4/README.md).
- Four independently selectable optional utilities, all **off by default**:

| Optional component | Version | License | Default |
|---|---|---|---|
| Message Center | 1.1.1 | GPL-3.0 | Off |
| Mute In Background | 1.1 | GPL-3.0 | Off |
| FPS Counter | 3.1 | Apache-2.0 AND zlib | Off |
| Graphics Settings (official) | 1.2.1 | GPL-3.0 | Off |

Selected components include their license notices and preserved corresponding source. Mute remains disabled by its native default until enabled in its generated configuration. Graphics Settings offers supported startup values through its config file; no advanced configuration menu or complete text-only resolution/display workflow is promised.

The installer checks the selected directory, presents an exact file plan, asks for installation consent, preserves matching files and keeps backups/journals for recovery. Users need no separate Python installation or Backend folder.

## Compatibility

- Original **VR Kanojo (2018)**; owner-tested with **v1.31**.
- **Confirmed test environment:** Windows X-Lite Optimum, a modified Windows 11 Pro x64 configuration. Prior baseline owner testing included fresh installation/reinstallation, game launch and Desktop controls without separate Python. Current v1.1.0 reports cover installation/gameplay, all four optional mods and the footer fix; no new reinstall matrix is claimed.
- Other Windows configurations, including stock Windows 10/11, have **not been independently verified**. These results do not establish universal Windows compatibility. Windows 11 ARM, older Windows and other game builds are not qualified.
- Recognized layouts: `VRKanojo.exe` + `VRKanojo_Data`, or `VR_Kanojo.exe` + `VR_Kanojo_Data`. Required Unity/Mono/managed evidence is validated; names or a renamed folder alone do not prove compatibility.
- **VR-Kanojo (2025) is unsupported.** The installer supplies no game files or game-version upgrade.

## Download and install

Obtain the installer, matching corresponding source and `SHA256SUMS.txt` from the **[official release page](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases)**. Check the exact downloaded version against its published SHA-256. No separate Python installation or Backend folder is needed.

1. Close the game and back up your game folder and user data. Use a separate writable copy for initial testing.
2. Run the single EXE normally. Review the scrollable runtime conditions; Accept continues and Decline exits. Administrator privileges are not normally required.
3. Browse to the directory containing the game executable and matching Data folder.
4. Choose any optional utilities and VR Kanojo Desktop or neither. All four utilities start unchecked. Review the target and file plan; use **Technical details** for paths and hashes.
5. Confirm installation explicitly and wait for verified completion. A matching reinstall may correctly report that no changes are required.
6. Launch the game yourself. The installer never launches it automatically.

See [installation](docs/INSTALLATION.md), [troubleshooting](docs/TROUBLESHOOTING.md) and [recovery](docs/RECOVERY.md). Keep `%LOCALAPPDATA%\FeriousX\VRKMI`; it contains persistent runtime, transaction and recovery data, not disposable setup files.

## If installation does not go as expected

- **Preparation takes several seconds:** allow the installer to finish checking files and preparing the plan. Avoid repeated Install clicks.
- **Invalid folder or plugin conflict:** select the folder containing the game EXE and matching Data folder. Do not enable FeriousX Desktop and original Play Without VR together.
- **Access denied, Windows security warning or startup failure:** follow [troubleshooting](docs/TROUBLESHOOTING.md) for safe checks and log locations. Verify official download hashes before running an unsigned build.
- **Interrupted installation:** keep the job ID and persistent state, let any active worker finish, then use the [recovery instructions](docs/RECOVERY.md).

## Differences from the original HF Patch

| Area | Historical HF Patch v1.1 | This installer |
| --- | --- | --- |
| Framework | BepInEx and a broad plugin selection | BepInEx 5.4.12 and required dependencies |
| Desktop controls | Original Play Without VR | Optional FeriousX VR Kanojo Desktop 1.0.4 |
| Extra utilities and development tools | Optional/default selections varied by preset | Optional Message Center, Mute In Background, FPS Counter and Graphics Settings; developer tools excluded |
| Uncensor support | Loader, redirector and model collection | Not bundled |
| Repair/update files and replacement save | Historical installer options/rules | Not bundled or performed |
| File operations | Legacy installer backup/cleanup flow | Checked plan, consent, ownership, verified backups and persistent recovery |

Read the [detailed comparison](docs/ORIGINAL_HF_PATCH_COMPARISON.md) and [manual mod guide](docs/MANUAL_MOD_INSTALLATION.md). Desktop improves the desktop-control role; it does not replace uncensor loaders, graphics utilities or developer tools. Original Play Without VR and FeriousX Desktop must never be enabled together.

## Known limits

- No game repair/update assets, uncensor models, replacement saves, automatic translation, general upgrade or uninstall workflow is provided.
- The Fist percentage is a requested cosmetic setting; visible finger clenching was not working in owner testing. It must not be described as verified animation.
- Unknown conflicting files and incompatible configurations are refused rather than force-overwritten. Filename-based desktop conflict checks do not guarantee detection of renamed plugins.
- Local directories only; symlinks/junctions and unsafe layouts are rejected. Conservative path-length and same-volume restrictions apply. See troubleshooting.
- This release EXE is unsigned. Host tests do not qualify clean Windows, every display/DPI combination, power-loss durability or hostile file races.

## Source, licenses and credits

[ManlyMarco and original HF Patch contributors](https://github.com/ManlyMarco/VRK-HF_Patch) provided the original installer lineage and plugins. FeriousX maintains this independent project and Desktop. See [credits](CREDITS.md).

Project source is GPL-3.0; inherited files retain their original notices, including GPL-3.0-or-later where stated. Bundled components have separate licenses. [LICENSE](LICENSE), [third-party notices](THIRD_PARTY_NOTICES.md) and the [component audit](docs/license-audit.csv) explain those obligations. Runtime Windows conditions apply to Microsoft Distributable Code, not to the GPL application as a whole.

[Build instructions](docs/BUILDING.md) document the official Python 3.14.10 runtime, pinned PyInstaller 6.22.3 and Inno Setup 7.1.1 toolchain. The clean corresponding-source export excludes compiled installers, plugin DLLs, game assets, credentials and recovery state. Build workspaces separately stage the verified payload for building. The built binary and matching source ZIP are separate assets; their published identities are recorded in [artifact metadata](docs/RELEASE_ARTIFACTS.json). No future features or dates are promised by this release scope.

## Repository navigation

- [Documentation index](docs/README.md) — user guides, development notes and historical evidence.
- [Architecture and current source layout](docs/ARCHITECTURE.md).
- [Installation](docs/INSTALLATION.md), [troubleshooting](docs/TROUBLESHOOTING.md) and [recovery](docs/RECOVERY.md).
- [Build instructions](docs/BUILDING.md) and [test guide](docs/TESTING.md).
- [Third-party licenses and notices](THIRD_PARTY_NOTICES.md) and [license audit](docs/license-audit.csv).
- [Contribution guidance](CONTRIBUTING.md).

The owner also confirmed installation and gameplay with the Phase10E architecture-maintenance local test on original VR Kanojo v1.31. This is owner-reported evidence, not a claim that all recovery, DPI or stock-Windows tests passed. See [maintenance source metadata](docs/RELEASE_PREPARATION.json).
