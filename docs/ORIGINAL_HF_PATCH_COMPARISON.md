# Comparison with original VR Kanojo HF Patch v1.1

This independent FeriousX project modernizes the original installer lineage; it does not claim all historical HF Patch features. The comparison uses previously inspected v1.1 source/component rules, extracted payload mappings and original plugin credits. It does not infer behavior by executing the old installer.

| Component or operation | Historical v1.1 evidence | Current v1.0.0 profile |
| --- | --- | --- |
| BepInEx | 5.4.12 framework; developer variant option | 5.4.12 x64 release framework and exact required dependencies included; developer variant excluded |
| Entry-point configuration | Game-specific BepInEx settings | Checked settings: UnityEngine.dll / MonoBehaviour / .cctor; preserve compatible user settings, refuse unsafe conflicts |
| Desktop controls | Play Without VR 1.0; optional mouse configuration | FeriousX Desktop 1.0.4 serves the desktop-control role, or choose neither. No legacy mouse-config overwrite. Original plugin not bundled |
| Message Center 1.1.1 | On-screen plugin message output | Excluded from initial payload |
| Mute In Background 1.1 | Background audio option | Excluded |
| Graphics Settings 1.2.1 | Additional graphics settings | Excluded |
| FPS Counter 3.1 | Performance overlay/statistics | Excluded |
| Runtime Unity Editor 2.4 / Script Loader 1.2.4 | Runtime inspection and C# scripting | Excluded |
| Historical configuration UI 16.3 | Included in the original plugin selection | Outside this release scope; no manual-install recommendation |
| Uncensor Loader 1.0 + Resource Redirector 1.1.3 | Loader/selector and resource-redirection support | Both excluded; neither a model package nor a replacement for one |
| Uncensor model collection | Separate historical assets | Not distributed; no model installation |
| Game repair/update payload | Historical Patch selection and file rules | Not distributed; no update/repair performed |
| Full save | Replacement save option | Not distributed; no save replacement |
| Legacy helper/cleanup/config tasks | Permissions/process/cleanup routines and preset rules in reviewed source | Not reused as an installation mechanism; no broad legacy directory deletion or forced process termination |
| Transaction/recovery | Legacy ZIP backup flow without the new coordinator guarantees | Per-plan consent, ownership/path/hash checks, verified backups, journals and persistent recovery |

The original preset rules did not select every plugin identically; the table lists available historical components, not a claim that every original installation included them. Original source inspection also identified inactive/no-op routines, so advertised historical intentions are not presented as newly verified capabilities.

Nine optional groups were excluded because their exact distributed-binary/source/license closure was not completed for this initial release: Message Center, Mute In Background, Graphics Settings, FPS Counter, Runtime Unity Editor, Script Loader, original Play Without VR, Uncensor Loader and XUnity Resource Redirector/Common. Exclusion is a packaging decision, not a claim that personal use is prohibited or that every upstream release is incompatible. A user installing separate mods must follow their licenses and version requirements.

No automatic translation feature is qualified in the current profile. An original project's broad description is not proof that a particular translator asset was in the examined v1.1 payload. No existing external plugin is automatically deleted merely because this installer does not bundle it.

No future feature or schedule is part of the v1.0.0 compatibility promise. Instructions for other optional plugins, where supported by upstream documentation, are in [Manual mod installation](MANUAL_MOD_INSTALLATION.md).

## Evidence

- [Original HF Patch source](https://github.com/ManlyMarco/VRK-HF_Patch), especially components.iss and Plugin Readme.md; original extracted evidence is preserved privately, not redistributed.
- [Original VRKanojo plugins](https://github.com/ManlyMarco/VRKanojo_Plugins).
- Current [component catalog](../manifests/real-components.json), [license audit](license-audit.csv), [embedded file inventory](EMBEDDED_FILE_INVENTORY.json) and [release readiness](RELEASE_READINESS.md).

Original authorship: ManlyMarco and contributors. Independent modernization and maintenance: FeriousX. GPL terms and third-party attributions remain applicable.
