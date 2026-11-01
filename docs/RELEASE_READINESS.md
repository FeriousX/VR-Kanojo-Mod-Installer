# Phase 8D release readiness

## Assessment

**Documentation/source preparation complete; final artifact promotion held pending clean-Windows qualification and owner approval.** Target name is VR Kanojo Mod Installer v1.0.0. Current binary remains the exact, unchanged Phase 8C.3A RC; no final filename, metadata, signature or public release was fabricated.

## Evidence reused

- Owner explicitly confirmed the corrected license dialog fits, explicit acceptance and GUI navigation work, excluded options are not offered, fresh installation/reinstallation succeed, VR Kanojo launches, and Desktop controls work. The confirmed environment is Windows X-Lite Optimum (modified Windows 11 Pro x64), with no separate Python installation required. Other Windows configurations have not been independently verified. These are owner observations, not new agent gameplay tests.
- Existing 8C.3 evidence: 26 packaged checks, 8 focused recovery tests and 12 artifact checks. Existing 8C.3A evidence: 15 focused checks plus available-desktop GUI observations. These are reused, not newly rerun or re-counted as Phase 8D tests.
- Existing licenses, full source/notice associations and official Python 3.14.10 provenance remain cleared for the reduced profile. No changed binary requires reopening those investigations.
- New Phase 8D checks verify code/source consistency, all 80 resources, physical 27-file profile, excluded mappings, actual source-only export, notices, documentation and checksums. Results are recorded outside the source tree in verification.json.

## Current qualification

| Area | Result |
| --- | --- |
| Owner functional/gameplay testing of corrected RC | APPROVED by owner |
| License dialog on available desktop | Verified by owner and prior GUI check |
| All six requested resolution/scaling render combinations | NOT VERIFIED interactively; six geometry cases passed earlier |
| Clean Windows 10 x64 without dev dependencies | NOT VERIFIED |
| Clean Windows 11 x64 without dev dependencies | NOT VERIFIED |
| Single-EXE embedded runtime/resource integrity | Verified against retained build inputs |
| Installer signing | NotSigned |
| Final 1.0.0 versioned build | Not performed; RC preserved |
| GitHub publication | Not performed; owner-managed |

No clean Windows guest was available to this run; standard Hyper-V/VirtualBox/VMware command tools were not exposed. That is not evidence that no VM exists anywhere on the owner's machine. Host fixtures and gameplay approval do not substitute for clean-machine tests.

## Owner's shortest next steps

1. Use CLEAN_WINDOWS_TESTING.md in clean Windows 10/11 x64 standard-user snapshots, without development Python or copied private AppData. Record pass/fail for runtime launch, license accept/decline, installation, reinstall, conflicts, interrupted recovery and retained state. Use disposable game copies and launch games only manually.
2. Record any remaining display-scale checks relevant to release support; no claim of six-setting interactive qualification has been made.
3. Once qualification is accepted, authorize/build a final metadata-only 1.0.0 artifact from this exact code, verify its new hash and matching source. Do not simply rename the RC.
4. Review GPL/third-party notice and matching-source delivery, then publish personally through the owner's GitHub account. No Git operation, repository initialization, tag, release or publication was performed here.

## Source export

The GitHubSource directory contains application/backend/wizard/build source and selected synthetic tests, full current license texts, Desktop corresponding source/assets, the reduced component catalog and current documentation. It omits obsolete private audit reports and old runtime reference collections. Those historical inputs remain untouched in their original workspace locations. The binary is outside the source directory and normal source history.

Existing legacy UI source comments/archived component catalog reference fields can describe earlier synthetic phases; current runtime behavior and approved selections are documented by the current manifest/resource inventory, not by those comments. No backend or GUI implementation change was made to rewrite history or implement a new feature.

The owner's documentation correction is applied: the old configuration UI appears only as a historical scope fact, no manual-install recommendation is made, and no new menu availability, feature commitment or date is promised.
