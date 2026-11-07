# Graphics Settings usage and limits

Optional and off by default. Requires the supplied BepInEx framework and its Harmony compatibility components. Configuration Manager is not installed or required as a hard DLL dependency; no advanced configuration menu is supplied.

After a first game run creates its native configuration, close the game before editing supported startup values and restarting. Source supports startup frame-rate limit, VSync, anti-aliasing, anisotropic filtering and run-in-background settings. This workflow remains untested in VR Kanojo. Do not assume every setting applies on restart: resolution uses a custom UI drawer, and display/monitor settings have additional native event behavior. No hot-reload or advanced menu is promised. Native defaults can affect frame pacing and background execution; gameplay qualification remains pending.

The installer does not create or replace this plugin's user configuration. Existing unknown or different plugin files are subject to the existing ownership/conflict/backup/consent safeguards, not forced replacement. No Configuration Manager, Vectrosity or game DLL is added.
