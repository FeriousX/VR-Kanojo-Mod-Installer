# Troubleshooting

## Confirmed Windows environment

The owner tested **Windows X-Lite Optimum (modified Windows 11 Pro x64)**: fresh installation, reinstallation, game launch and VR Kanojo Desktop controls worked, without installing Python separately. Other Windows configurations have **not been independently verified**. This is not universal Windows compatibility or clean stock-Windows qualification.

## Preparation takes several seconds

The installer hashes files, validates the selected folder and prepares a checked operation plan. Several seconds are normal. Wait for a result and avoid repeatedly clicking Install. Installation remains blocked until a valid plan is ready. If preparation reports an error or does not finish, open **Technical details**, record the exact error and job ID, and check the locations below. A moving progress bar alone is not a successful installation.

## Invalid game directory

Choose the folder containing `VRKanojo.exe` and `VRKanojo_Data`, or the recognized `VR_Kanojo.exe` / `VR_Kanojo_Data` layout. Do not select a parent folder or the Data folder itself. This installer is for original VR Kanojo (2018), owner-tested with v1.31; the 2025 game is unsupported.

The executable, Unity 5.4.5p1, required managed/Mono files and application identity must pass validation. A renamed folder or matching filename is insufficient. Do not rename executables or download substitute game DLLs to make validation pass. Keep the precise rejection message if a complete legitimate copy is refused.

## Existing mod or plugin conflicts

Matching files and compatible settings are preserved. Unknown replacements or incompatible settings are blocked. Back up affected files and resolve the specific conflict in a separate copy; do not delete the whole BepInEx directory or force an overwrite.

**FeriousX VR Kanojo Desktop and original Play Without VR must not run together.** An existing alternative is not automatically deleted. A renamed DLL can still be loaded by BepInEx and may evade filename-based conflict checks. If changing desktop plugins deliberately, keep the unused plugin outside all loader directories rather than merely renaming its DLL. Follow the [manual mod guide](MANUAL_MOD_INSTALLATION.md) and exact upstream version instructions for other external mods.

## File permission or path errors

Close the game first and make sure another installer/worker is not still using the target. Use a normal local, user-writable game copy under the same Windows account. Check available disk space and whether security software has reported a blocked or quarantined file; do not disable that protection to bypass an error.

Local non-root paths are required. UNC/network paths, symlinks and junctions are unsupported. The conservative path budget is 259 characters, and target/persistent state must share a volume. A shorter user-writable path can resolve an excessive-path-length error. Do not change system permissions, switch accounts, or assume Run as administrator fixes ownership or recovery errors. Preserve `%LOCALAPPDATA%\FeriousX\VRKMI` and obtain guidance before relocating an installation with active transactions.

## Windows SmartScreen or download warnings

The current pre-release EXE is **unsigned**, so Windows may display an unrecognized-app/unknown-publisher warning. That warning is not proof that a file is safe or malicious. [Microsoft explains SmartScreen reputation](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation).

1. Verify that the download comes from [FeriousX/VR-Kanojo-Mod-Installer Releases](https://github.com/FeriousX/VR-Kanojo-Mod-Installer/releases), when the owner makes the pre-release available, rather than an advertisement, mirror or forwarded attachment. For a private test build, use the exact file supplied by the owner.
2. Compare the exact filename and SHA-256 with the checksum published alongside that same build. The privately prepared RC's identity is in [artifact information](RELEASE_ARTIFACTS.json). In PowerShell, for example:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath '.\VRK-Mod-Installer-v1.0.0-rc.8C3A-Private.exe'
   ```

3. If the hash differs, the source is uncertain, or security software identifies a threat, do not run it; obtain the correct file or contact the maintainer. A matching hash verifies consistency with that reference, not universal safety.

Do not disable SmartScreen/antivirus or change system security policy. Review the warning and verify the source before deciding whether to run any unsigned program. No signed-publisher identity is claimed for this RC.

## Interrupted installation or uncertain result

Do not launch the game until the transaction outcome is known. Keep the job ID and error details. Closing the wizard does not intentionally terminate an active worker; allow it to finish and never terminate an unrelated process. After the worker exits, follow [Persistent recovery](RECOVERY.md) using the matching retained runtime and the same Windows account.

Do not delete journals, backups, receipts, cached runtime files or authorization data to clear an error, and do not reuse a spent approval. A failed or uncertain transaction is not a successful installation. Recovery may complete, roll back or refuse a conflict; preserve the records if it cannot safely reconcile.

## BepInEx or Desktop does not start

After verified installation completion, launch the game manually and inspect `BepInEx/LogOutput.log` in the selected game directory, when disk logging is enabled. Keep the full error and the affected plugin name. If the log does not exist, BepInEx may not have initialized or disk logging may be disabled; absence alone does not identify the cause.

Check that you launched the same original-game copy selected in the installer, the expected `winhttp.dll`, `doorstop_config.ini` and `BepInEx/core` files are present, and Desktop was actually selected. With the **neither** option, absence of Desktop controls is expected. Check again for a second desktop plugin and incompatible manually installed mods. Do not replace the framework with arbitrary newer BepInEx/Harmony files or copy game DLLs from another build. Preserve the error and seek guidance if the verified files still fail to load.

## Useful diagnostics

| Information | Where to find it |
| --- | --- |
| Installation error, plan and job ID | Installer **Technical details** |
| Persistent per-job presentation/diagnostic records | `%LOCALAPPDATA%\FeriousX\VRKMI\state\out\gui-install\<job-ID>\` (`frame.json`, `frame.ini`, `job.json` when created) |
| Backup/journal and recovery state | `%LOCALAPPDATA%\FeriousX\VRKMI\state\`; use the job's recorded paths and [recovery guide](RECOVERY.md), not guessed record edits |
| Retained verified runtime and recovery helper | `%LOCALAPPDATA%\FeriousX\VRKMI\packages\<matching-bundle>\` |
| Early backend startup error | Setup's temporary `hf-startup-<job-ID>.txt` file, when created; record the displayed error before closing because temporary files may be cleaned up |
| BepInEx/plugin runtime log | `<selected-game-folder>\BepInEx\LogOutput.log`, when disk logging is enabled |

When asking for help, provide the build filename/hash, Windows configuration, exact error, job ID and relevant redacted log lines. Do not upload your entire state folder, backups, game files, DPAPI credentials or authorization secrets. [Installation instructions](INSTALLATION.md) and the [clean-Windows checklist](CLEAN_WINDOWS_TESTING.md) describe the remaining scope and qualification limits.
