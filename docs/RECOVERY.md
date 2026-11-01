# Persistent recovery

State resides at `%LOCALAPPDATA%\FeriousX\VRKMI\state`; retained verified runtime versions reside under `%LOCALAPPDATA%\FeriousX\VRKMI\packages`. Journals, backups, ownership/consent replay records and Windows CurrentUser DPAPI-protected authorization data are outside setup's temporary extraction directory. Do not delete them as temporary files or copy credentials between accounts.

Closing the wizard does not intentionally terminate an active worker. Keep the displayed job ID and allow that worker to finish. After it has exited, use the **matching retained runtime for that transaction** from the same Windows account. Do not choose a bundle by guessing which is newest.

```powershell
& "$env:LOCALAPPDATA\FeriousX\VRKMI\packages\<matching-bundle>\Recover.ps1" -Job '<64-character-job-ID>'
```

The release's runtime bundle is `81896c44bd1ee122`. Its helper verifies its pinned resource manifest and hashes before invoking recovery. Earlier transactions may need an earlier retained bundle. Respect local script policy. A verified matching cached `Backend/HFBackend.exe private-gui recover --job <job-ID>` is the existing native alternative if scripts are disallowed; obtain maintainer guidance if uncertain. Never weaken checks or delete journals to make a refusal disappear.

Recovery may report reconciled completion, rollback, conflict or uncertainty. A recovered failure is not a successful installation, and spent consent does not authorize another execution. Preserve user-modified files and error details; do not manually restore unrelated files or terminate unrelated processes.

Power-loss durability, hostile administrators/races, key compromise, old-state migration, general upgrades/uninstall and cache retirement remain unqualified. Recovery records are private user data and must never be included in a public source package.
