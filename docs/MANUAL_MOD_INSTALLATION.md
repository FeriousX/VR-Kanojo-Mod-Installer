# Optional mods installed separately

These mods are **not bundled** in this installer. Their exclusion reflects the initial payload's scope/licensing-source qualification, not an automatic ban on personal installation. The repositories below are verified upstream references; the installer does not endorse arbitrary current downloads as compatible with original VR Kanojo v1.31.

## Before adding a mod

1. Close the game. Back up the affected files, configurations and saves; preferably test a separate game copy.
2. Keep BepInEx **5.4.12 x64 / Mono** for this qualified profile. Select a plugin build explicitly compatible with BepInEx 5, old Unity and the original game's CLR/.NET environment. BepInEx 6/IL2CPP or a similarly named 2025-game mod is not an interchangeable substitute.
3. Download from the author's release page. Read that exact archive's README and dependencies. Keep its license/source information; this guide is not permission to redistribute it.
4. Extract to a temporary staging folder and inspect the tree first. Plugin DLLs usually belong under `BepInEx/plugins`; libraries or patchers may have different destinations. Preserve documented subdirectories. Do not overwrite the qualified framework or unknown files just because an archive contains them.
5. Add one mod at a time. Launch the game manually, inspect `BepInEx/LogOutput.log`, then close it before changing anything else. To undo a manual addition, restore only your own backed-up files. Installer receipts do not automatically own or uninstall manually added mods.

## Message Center and Mute In Background

[Official BepInEx Utility repository](https://github.com/BepInEx/BepInEx.Utility) · [Releases](https://github.com/BepInEx/BepInEx.Utility/releases)

Message Center displays plugin Message-level log entries on-screen; it is not required for a plugin to log. Mute In Background provides an audio option for an unfocused game. Both were excluded from the installer payload.

Upstream documents BepInEx 5 Mono and DLL placement under `BepInEx/plugins`. For a separately qualified compatible build, place only the chosen plugin there, without replacing BepInEx core. After a manual first launch, edit its generated `.cfg` under `BepInEx/config` while the game is closed if configuration is needed. Use the exact version's keys and documented options; this guide does not invent them. Historical versions were Message Center 1.1.1 and Mute In Background 1.1; current versions have not been gameplay-qualified here.

## FPS Counter

[Official FPSCounter repository](https://github.com/ManlyMarco/FPSCounter) · [Releases](https://github.com/ManlyMarco/FPSCounter/releases)

Provides frame/performance statistics. It was excluded with the optional utilities. Choose a BepInEx 5 Mono-compatible release; stage the archive, preserve its `BepInEx/plugins/FPSCounter` layout where supplied, and merge only the reviewed plugin files. The historical 3.1 package used a flatter DLL path, so do not duplicate the same plugin in both locations. Use the exact release's hotkey and generated `.cfg` instructions. Do not replace the framework with a newer major version. Placement is upstream-documented; current-release compatibility with v1.31 remains unverified.

## Runtime Unity Editor

[Official RuntimeUnityEditor repository](https://github.com/ManlyMarco/RuntimeUnityEditor) · [Releases](https://github.com/ManlyMarco/RuntimeUnityEditor/releases)

An optional debugging/editor tool capable of changing live game objects. It was excluded from the normal installer profile. Upstream supplies distinct loader builds: choose a BepInEx 5 Mono archive only after checking its old-Unity support. Inspect its BepInEx tree, preserve plugin subdirectories and required companion DLLs, and copy only reviewed additions. Follow the exact release's activation key; current upstream documents F12. Do not add an arbitrary Vectrosity DLL to suppress an optional warning. The historical 2.4 files were inspected; a newer release is not qualified by that fact.

## Original Play Without VR — alternative, never an addition to Desktop

[Official VRKanojo plugins repository](https://github.com/ManlyMarco/VRKanojo_Plugins) · [Releases](https://github.com/ManlyMarco/VRKanojo_Plugins/releases)

Provides the original mouse/keyboard mode without a connected headset. Its role is served by FeriousX Desktop in this installer, and its binary is excluded. **Never enable `VRK_PlayWithoutVR.dll` and `VRKanojoDesktop.dll` together.** To evaluate the original plugin, use a separate copy installed with the **neither** choice. Preserve any installed Desktop DLL outside the plugin directory before deliberately changing an existing setup; do not leave a renamed DLL that BepInEx will still load.

The original upstream instructions require BepInEx x64 at least 5.4.4, the MonoBehaviour entry point, SteamVR installed and no connected HMD. This installer uses 5.4.12 and the game-specific entry-point template, but does not establish all SteamVR conditions on your machine. Inspect the original release archive, copy only its intended Play Without VR files into the matching game tree, and do not copy an unrelated save, framework or configuration package. This alternative is not part of this installer's gameplay qualification.

## Uncensor Loader and XUnity Resource Redirector

[VRKanojo plugins](https://github.com/ManlyMarco/VRKanojo_Plugins) · [XUnity upstream](https://github.com/bbepis/XUnity.AutoTranslator)

Uncensor Loader selects compatible separately prepared models; Resource Redirector supplies its redirection dependency. **Neither plugin nor any model collection is bundled here.** A loader cannot create missing assets. Obtain any assets legally from their authors with permission; this project supplies no uncensor asset download or redistribution route.

The historical mapped layout was `BepInEx/plugins/VRK_UncensorLoader.dll`, redirector DLLs under `BepInEx/plugins/XUnity.ResourceRedirector`, and `BepInEx/core/XUnity.Common.dll` for its matching dependency. This is historical path evidence, not instructions to mix current XUnity archives or install a full translator. Verify the selected loader, matching redirector/common versions, their archive layout and asset format as a complete set first. Do not replace unrelated core files. The native configuration can be edited in generated `BepInEx/config` files according to the plugin documentation; model changes may require a scene reload or restart. A complete compatible asset/dependency combination has **not** been qualified for manual installation here, so no ready-to-run recipe is claimed.

## Graphics Settings

[Official GraphicsSettings repository](https://github.com/BepInEx/BepInEx.GraphicsSettings)

Exposes additional graphics settings; excluded from this payload. Upstream documents a separate configuration UI as part of its normal workflow. This project provides **no validated independent setup procedure** for that workflow, and does not recommend installing the historical menu. An upstream repository link is supplied for reference, not as a claim of supported installation in this profile.

## C# Script Loader

[Official ScriptLoader repository](https://github.com/ghorsington/BepInEx.ScriptLoader) (formerly denikson/BepInEx.ScriptLoader)

Compiles and runs user C# scripts. It was excluded with the developer tools. Upstream targets BepInEx 5.4 and requires `System.Reflection.Emit`; a .NET Standard/IL2CPP-targeted environment is not a substitute. Historical payload evidence places `ScriptLoader.dll` under `BepInEx/plugins`; the current upstream README has a singular `plugin` spelling, so follow a verified BepInEx 5 release archive rather than creating a competing loader directory.

After independently qualifying that plugin, upstream places script `.cs` files in a game-root `scripts` folder and can run their Main methods automatically. Install only code you have reviewed and trust; restarting is safer than assuming every script cleans up on reload. This guide does not provide scripts or qualify a new compiler bundle.

## Repair/update assets, replacement saves and legacy configs

No verified redistributable repair payload, replacement-save source or complete current installation procedure is provided here. Do not download game DLLs or use a full-save file to repair a mod-loading error. Use your legitimate game distribution's own update/verification process after backing up your data, and follow its documented consequences for existing mods. The installer neither runs that process nor guarantees the recovery of removed historical features. Do not import old global mouse configs or broad cleanup routines over a working Desktop setup.

This guide documents available procedures and their limits, not a future-feature roadmap. Manual modifications remain outside the installer's transaction and rollback records.
