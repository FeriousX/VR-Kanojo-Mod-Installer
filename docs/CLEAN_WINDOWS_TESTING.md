# Clean Windows qualification — NOT VERIFIED

No clean Windows 10 or Windows 11 guest was used for this milestone. Host/source/packaged fixture tests and the owner's gameplay approval do not establish a clean-machine pass.

Use fresh Windows 10 x64 and Windows 11 x64 snapshots with a standard user, no Python, Codex, Visual Studio or development toolchain. Do not copy the maintainer's AppData state or DPAPI credentials into the guest.

1. Copy only a verified, qualified installer EXE. Check the recorded size/SHA-256. Try ordinary Downloads, a path with spaces and reasonable nesting. Record OS build, user/elevation state and any security dialog without bypassing operating-system protections.
2. Manually supply an authorized disposable compatible game copy inside the guest; never point the test at the owner's original/host Steam installation. Keep it closed during installation.
3. Verify Browse/manual folder validation, missing/wrong-layout/architecture evidence and safe errors. For the essential-only profile, test FeriousX Desktop and neither; confirm excluded optional/original-desktop choices cannot be requested. Use separate disposable roots.
4. Observe preparation feedback. Review component/count/hash details. Test Cancel with no file changes, then approve the exact plan. Confirm genuine stages and committed completion. The current fresh core + FeriousX profile has 27 mapped files; other choices differ. Do not treat a no-op reinstall as a new commit.
5. Test matching reinstallation, user configuration preservation, unrelated files and conflicting desktop plugins. Unknown replacements must block rather than silently overwrite.
6. Close/relaunch the wizard during a dedicated disposable transaction without terminating unrelated processes; let its worker finish. After it exits, exercise matching-cache recovery and repeated reconciliation. Move/remove only the test EXE and confirm state/cache survives setup temp cleanup. Preserve uncertain records. Hard-kill/power-loss durability is not automatically qualified by this test.
7. Verify missing/tampered runtime resources fail closed in an isolated test cache, restoring only verified bytes. Do not delete essential persistent state to bypass refusal.
8. Launch the guest's game manually afterward and record BepInEx/plugin loading and the owner's required controls. Gameplay compatibility is a separate manual result, never an installer success inference.

Keep redacted evidence and explicit PASS/FAIL/NOT VERIFIED per OS/profile. The release retains the stated unverified-environment limitations. Stable-release qualification remains pending; do not claim clean-machine success until the recorded checks actually pass.
