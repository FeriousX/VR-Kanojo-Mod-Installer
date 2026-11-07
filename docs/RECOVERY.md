# Persistent recovery — v1.1.0 guidance

State: `%LOCALAPPDATA%\FeriousX\VRKMI\state`. Verified retained runtime packages: `%LOCALAPPDATA%\FeriousX\VRKMI\packages`. Journals, backups, ownership/consent replay records and Windows CurrentUser DPAPI authorization data remain outside temporary extraction. Keep them; do not copy credentials to another account.

Closing the wizard does not intentionally terminate a worker. Retain its displayed job ID, let the worker finish, then recover with the **exact verified runtime retained for that transaction**, under the same Windows account. Determine the matching package from its recorded job/runtime information; do not guess the newest bundle or use a fixed historical ID.

```powershell
& "$env:LOCALAPPDATA\FeriousX\VRKMI\packages\<matching-transaction-bundle>\Recover.ps1" -Job '<64-character-job-ID>'
```

The helper verifies its pinned resources before recovery. A verified matching `Backend/HFBackend.exe private-gui recover --job <job-ID>` remains the alternative if local script policy disallows the helper; seek maintainer guidance rather than weakening policy/checks. Do not terminate unrelated processes, force transitions or delete records to clear a refusal.

Recovery may reconcile completion, roll back, or report conflict/uncertainty. Recovered failure is not installation success; spent consent cannot authorize another execution. Preserve user-modified/unrelated files and error details. Transaction-specific data and the matching retained package remain authoritative even after a newer installer is downloaded or moved.

The candidate's actual bundle is recorded in EMBEDDED_FILE_INVENTORY.json. That is not a universal recovery default: older transactions may require a different retained package. Never change older transaction mappings after building a new installer.

Owner recovery retest remains NOT VERIFIED. Synthetic recovery tests passed in Phase9E1; power-loss durability, hostile races/admins/key compromise, old-state migration, general upgrades/uninstall and cache retirement remain unqualified. Never include private recovery records in a public source archive.
