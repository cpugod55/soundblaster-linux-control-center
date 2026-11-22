## v3.3.7 — Community testing pre-release (renamed from verified v3.3.68-test4)

- Same audio behavior as hardware-tested v3.3.68-test4, with package/version metadata renamed to v3.3.7.
- Automatic device selection remains governed by the OS/WirePlumber; a user-level background observer restores selected Sound Blaster EQ, AC3 5.1, and Speaker Fill when returning from other devices.
- Keeps manual **Use Sound Blaster** action and experimental warnings for analog layouts beyond 2.1.
- Maintainer verified Ubuntu KDE hardware, including approximately 1–2-second return-to-surround recovery with GUI closed. Further distro/hardware reports requested.

## v3.3.68-test4 — repair background Speaker Fill restore (experimental)

- Fixes a confirmed `NameError: update_fill_processing is not defined` when using the GUI-independent `--restore-selected` command. It previously ran before its Speaker Fill and stream-enumeration functions were defined.
- Moves only the required headless helper function definitions before the CLI dispatch; preserves the GUI's DSP and processing behavior.
- Reports an incomplete restore if Speaker Fill control programming fails, instead of misleadingly logging success.
- Adds a regression test checking that the headless command runs after all of its required functions are defined.
- This remains an experimental release; Ubuntu/KDE device testing and cross-distribution hardware validation are still required.

## v3.3.68-test4 — background return-to-speakers recovery (experimental)

- Adds a background, GUI-independent audio return observer using standard PipeWire/Pulse compatibility interfaces, run under systemd --user.
- A selected Sound Blaster card may have its saved surround profile and EQ reasserted after headset disconnect. Never forces selection of an unrelated output.
- Retains digital 5.1, v3.3.65 relaunch safety, test1 Use Sound Blaster button, and experimental analog >2.1 warnings.

## 3.3.65
- Prevent rapid repeated Output Setup changes from racing the relaunch/audio-settling cycle. Apply, Connection, and Speaker Layout are disabled while a change is being handed off.
- Show in-app Output Setup progress text, including a clear post-relaunch “audio is settling” message.
- Relaunched instances now carry an internal marker and enforce a 4.5-second settling window before another Output Setup change can be applied.

# 3.3.65

- Reworked Output Setup relaunch around a persistent per-user helper service instead of transient GUI services or terminal-owned `gtk-launch`.
- The installer now installs and starts `soundblaster-zse-relaunch-helper.service`; after audio reconfiguration the temporary setup terminal only sends the old GUI PID to that helper.
- The helper waits for the old GUI to be gone, then launches a fresh `~/.local/bin/soundblaster-zse-control` while remaining alive for subsequent layout/connection changes.
- Uninstall now disables and removes the relaunch helper service.

# 3.3.63

- Replaced the transient systemd-owned GUI relaunch after Apply Output Setup with the desktop-session launch path verified on KDE/Wayland.
- After output reconfiguration, the helper waits briefly and runs `gtk-launch soundblaster-zse-control`, matching a normal desktop-menu launch.
- Preserved the working digital logical-layout switching and existing DSP/fill behavior.

## 3.3.63
- Fix repeated Output Setup relaunches by giving every systemd --user transient relaunch service a unique PID + nanosecond unit name.
- Preserve the verified live Digital logical-layout switching and existing DSP paths unchanged.

## 3.3.63
- Fix Output Setup automatic relaunch by handing the replacement GUI to an independent `systemd --user` transient service.
- The relaunch service waits two seconds after output reconfiguration, then starts the control center; this replaces the unreliable terminal-owned `nohup`/PID-wait path.
- Preserve the verified digital logical-layout switching and Fill-engine behavior from 3.3.60.

## 3.3.63
- Fix automatic GUI relaunch after Apply Output Setup by waiting for the exact old GUI PID to exit before starting the replacement instance.
- Preserve the verified digital logical-layout switching introduced in 3.3.57/3.3.58.

## 3.3.63

- Speaker Setup manual layout menu no longer includes `auto`; Auto is now exclusively a Connection mode.
- Leaving Connection=Auto initializes the manual layout selector from the currently detected live layout.
- Output Setup relaunch now waits for the old GUI single-instance lock to release and launches the replacement GUI detached from the temporary terminal.
- Preserves the verified v3.3.57 live Digital layout switching and v3.3.56 Fill/preset fixes.

## 3.3.57

- Fix custom preset recall status: the bottom status bar now updates to the selected custom preset instead of retaining the previous built-in preset name.
- No EQ/DSP recall behavior changed; this is a display-state fix only.

## 3.3.55
- Reorganized EQ preset management onto the main EQ & Levels page.
- Renamed Presets & Test to Speaker Setup.
- Added in-app Connection and Speaker Layout selectors using the existing distro-aware installer backend.
- Added selectable Application (preferred) vs PipeWire compatibility Speaker Fill engine.
- Preserved v3.3.53 DSP/settings behavior as the rollback baseline.

## 3.3.53 - 2026-09-09

- Add openSUSE Tumbleweed `zypper` dependency support, including `alsa-plugins-a52` and the LADSPA ZaMaxim package.
- Add an openSUSE persistent A52 path using the hardware-verified `plug:a52:<Creative ALSA card>` PCM; do not depend on `aplay -L` exposing an A52 hint.
- Enable both Creative `IEC958` and `IEC958 Default PCM` playback switches when available before creating the A52 sink.
- On clean Debian Live sessions, start the user PipeWire/WirePlumber/PipeWire-Pulse services before `pactl` card detection and emit a clear connection diagnostic instead of silently exiting.
- Deduplicate Debian dependency package names.
- Preserve v3.3.52 DSP, EQ, Speaker Fill, Bass Management, channel mapping, and Bazzite behavior.

## 3.3.52 - 2026-09-09

## v3.3.52 — Ubuntu explicit Speaker Fill test

- Extends the verified v3.3.51 explicit stereo-to-5.1 Speaker Fill DSP to Ubuntu native `iec958-ac3-surround-51` targets for direct listening tests.
- Preserves the v3.3.51 Fill topology and coefficients exactly: OFF front-only, PSD difference rears, FULL 0.75 rear duplication, 0.5+0.5 center and low-passed LFE, Rear Delay, and Stereo Width.
- Keeps Ubuntu EQ target/compatibility behavior unchanged; only stereo Speaker Fill routing is moved to the persistent explicit Fill sink.
- Keeps Bazzite on its already-verified compatibility Fill path unchanged.
- v3.3.51 remains the saved verified rollback checkpoint.

## 3.3.52 - 2026-09-09

## v3.3.52 — Mint Bass Management graph rebuild + blue accent

- Preserves the verified v3.3.50 explicit Speaker Fill DSP unchanged.
- On persistent A52/dedicated-Fill systems, Bass Management changes are now baked into the explicit six-channel EQ/bass graph and the user filter-chain service is recreated, instead of trusting live biquad/mixer property updates that Mint can acknowledge without applying audibly.
- Bass graph rebuild runs off the Tk thread and is debounced for LFE Trim slider changes.
- Reasserts EQ, preamp, channel calibration, and the verified Fill route after the filter-chain-only restart.
- Restores the Sound Blaster UI accent from red to blue.


- Replaces the non-Atomic A52 Speaker Fill channelmix path with an explicit 2-to-5.1 PipeWire filter-chain graph. OFF, PSD, FULL, Rear Delay, Stereo Width, Center synthesis, and Speaker Fill LFE low-pass are now owned by the application DSP instead of PipeWire's automatic channel mixer.
- PSD rear fill uses L-R / R-L ambience so centered dialogue is intentionally reduced in the rear channels; FULL duplicates left/right into the rears with controlled gain.
- The explicit graph outputs canonical `FL FR RL RR FC LFE` directly into `soundblaster_zse_eq` with remixing disabled on the graph output, making channel identity deterministic before EQ/Bass Management.
- Upgrading from v3.3.43-v3.3.49 removes only the old named `pw-loopback` Fill process before loading the explicit graph so a stale `soundblaster_zse_fill` node cannot be mistaken for the new DSP.
- Bazzite retains its previously verified compatibility loopback unchanged.
- Refreshes the visual system toward the AMD Linux Control Center family: neutral dark cards, red accent treatment, dashboard-style header/status chips, and matching slider accents.
- Preserves the v3.3.49 privacy-safe About links and Cinnamon `StartupNotify=false` fix.

## 3.3.49

- Restores the privacy-safe About/Package presentation lost during the v3.3.38 source sync: the maintainer email is no longer displayed in the application.
- Adds direct About-page buttons for the GitHub project, GitHub Issues, and GitHub Sponsors support page.
- Preserves all v3.3.48 Mint/older-PipeWire compatibility work, including Fill-loopback recreation on PipeWire older than 1.2 and Cinnamon startup-notification handling.
- Adds regression coverage so private contact text and project/support links cannot silently regress again.

## 3.3.48 - 2026-09-09

- Mint/older-PipeWire Speaker Fill compatibility: on PipeWire older than 1.2, recreate only the dedicated Fill loopback when OFF/PSD/FULL, Rear Delay, Stereo Width, or Fill LFE cutoff changes. Mint 22.3 testing showed live Props readback changed while the running channel mixer remained audibly unchanged.
- Wait for the old Fill sink to disappear before creating its replacement so stale nodes cannot satisfy readiness checks.
- Preserve the verified zero-restart live update path on newer Fedora/CachyOS PipeWire releases.
- Disable desktop `StartupNotify`; the Tk app does not complete Cinnamon's startup-notification protocol and could leave a busy cursor until clicked.

## 3.3.47 - 2026-09-09

- Fixes the dedicated A52 Speaker Fill route so its 2-channel-to-5.1 playback stream explicitly allows PipeWire channel remixing instead of contradicting the requested `channelmix.upmix` DSP with `stream.dont-remix=true`.
- Restores live OFF / PSD / FULL Speaker Fill behavior, Rear Delay, Stereo Width, and Speaker Fill LFE Crossover on the persistent A52 path used by Linux Mint, Fedora, and Arch/CachyOS digital 5.1 compatibility routing.
- Keeps the explicit six-channel Bass Management DSP graph enabled when the EQ uses A52 compatibility targeting; compatibility routing now changes target attachment only and no longer silently disables Bass Management.
- Bass Management persistence preserves A52 `target.object` routing while regenerating the six-channel graph.
- Preserves the verified Bazzite compatibility graph unchanged.
- Retains the v3.3.46 Linux Mint meter/analyzer and non-blocking Fill-maintenance fixes.

## 3.3.46 - 2026-09-09

- Fix Linux Mint 22.x Live Output Levels and spectrum capture on PipeWire builds whose `pw-record` does not support the newer `--raw` option. The app now capability-detects `--raw` and uses the compatible stdout capture form when it is unavailable.
- Move persistent A52/Bazzite Speaker Fill stream maintenance off the Tk GUI event thread so the 1.5-second connection-status poll cannot stall controls on slower PipeWire releases.
- Serialize interactive Fill updates against background stream maintenance, preventing overlapping `pw-dump`/`pw-cli`/stream-move work while OFF/PSD/FULL is being changed.
- Preserve the v3.3.45 Mint/Debian A52 installer fixes, the v3.3.44 Fedora fixes, and the v3.3.43 persistent A52 Fill architecture.

## 3.3.45 - 2026-09-09

- Extended persistent Digital AC3/A52 5.1 setup to Debian/Ubuntu/Linux Mint systems when a native Creative AC3 profile is unavailable.
- Preserves native `iec958-ac3-surround-51` when the Creative card advertises it; otherwise dynamically discovers the Creative IEC958 ALSA card/device and creates `alsa_output.soundblaster_a52_51`.
- Debian-family A52 capability detection now recognizes installed `libasound2-plugins` even when `aplay -L` omits the `a52` PCM hint.
- Automatically enables the Creative IEC958 playback switch before handing the digital PCM to A52 when the mixer exposes that control.
- Explicit `--connection digital --layout 5.1` is fail-closed on non-Atomic supported systems and can no longer fall through to a headset, HDMI, or analog stereo sink.
- Debian/Ubuntu/Mint dependency setup now repairs stale `deb cdrom:` Live-media APT entries after a failed package-index update, backs up the affected source file, and retries.
- Retains all v3.3.44 Fedora fixes and the v3.3.43 persistent Fill-routing behavior.

## 3.3.44 - 2026-09-09

- Fedora Digital 5.1 now uses the same persistent A52/AC3 sink architecture validated on CachyOS, with Creative ALSA card/device discovery from `aplay -l` rather than hard-coded card numbers.
- Fedora A52 detection now accepts the installed `alsa-plugins-a52` RPM even when `aplay -L` omits the `a52` hint.
- If the Creative card exposes an `IEC958` playback switch, the installer unmutes it before creating the A52 sink. This fixes Fedora Live boots where the encoder opened correctly but S/PDIF playback was muted.
- Explicit `--connection digital --layout 5.1` on Fedora now uses the persistent A52 path and fails closed instead of falling through to an unrelated stereo USB/analog sink.
- Installer application version is isolated from `/etc/os-release`, preventing Fedora's OS `VERSION` value from replacing the Sound Blaster Control Center version in install output.
- Preserves v3.3.43 dedicated A52 speaker-fill routing and all prior stale-target and CA0132 fixes.

## 3.3.43 - 2026-09-08
- Fix CachyOS/Arch Digital 5.1 Speaker Fill routing regression found during live v3.3.42 testing.
- A52/AC3 targets now use the persistent `soundblaster_zse_fill` path, so changing OFF/PSD/FULL no longer restarts `pipewire-pulse` and tears down the AC3 sink.
- The connection-status loop keeps stereo application streams on the stable fill sink while native multichannel streams remain discrete.
- Installer writes non-global upmix defaults for the A52 target so the dedicated fill path owns stereo upmix behavior.

## 3.3.42 - 2026-09-08

- Fix CachyOS/Arch Digital 5.1 startup when the normal Creative IEC958 profile already owns the S/PDIF PCM.
- Digital 5.1 now releases the Creative ACP profile before starting the persistent A52/AC3 sink, preventing `Device or resource busy`.
- If A52 startup fails, the installer restores the previously active Creative profile instead of leaving the card disabled.
- Explicit Digital 5.1 still fails closed and never falls back to analog.

## 3.3.41 - 2026-09-08

- Fix CachyOS/Arch persistent A52 sink generation: correct PipeWire config escaping and correctly parse the Creative IEC958 ALSA device number from `aplay -l`.
- When `--connection digital --layout 5.1` is explicit, installation now stops on AC3 sink creation failure instead of silently falling back to analog.

## 3.3.40 - 2026-09-08

- Add installer output selection: `--connection auto|analog|digital` and capability-driven `--layout`.
- Add Arch/CachyOS Digital 5.1 A52 sink creation using the discovered Creative IEC958 ALSA device.
- Treat installed Arch `pcm_a52` as valid even when `aplay -L` does not advertise `a52`.
- Stop preserving unrelated stale USB/HDMI targets when a Creative card is present.
- Add clear fresh-Live pacman database action and improved Bazzite Atomic ACTION REQUIRED guidance.
- Preserve v3.3.39 same-device stale stereo-to-live-5.1 correction.

## 3.3.39

- Fixes an upgrade-path regression where a preserved `analog-stereo` EQ target could survive after the same device had switched to a live `analog-surround-51` sink, causing `soundblaster_zse_eq` to be regenerated as 2-channel stereo.
- Installer target preservation now follows only the exact live 5.1 sibling of a stale `analog-stereo` node; existing surround, AC3, unrelated stereo, and CA0132 physical channel-map behavior are unchanged.
- `--generate-eq-config` applies the same narrow live-sibling resolution so direct/config-generation paths cannot recreate the stale stereo target.
- Adds a regression test for the gjohnz v3.3.38 failure pattern: preserved stereo target + live 5.1 sibling must generate a 6-channel EQ targeting `analog-surround-51`.

## 3.3.38

- Fixes cross-distro LADSPA dependency installation: Arch/CachyOS now installs `zam-plugins-ladspa`; Fedora installs `ladspa-zam-plugins`; Bazzite/Fedora Atomic reports `ladspa-zam-plugins` as a required layered package when missing.
- Replaces raw `PermissionError` failures on root-owned `~/.config/pipewire` paths with a targeted ownership diagnostic and exact repair command, while continuing to refuse running the user-local installer with sudo/root.
- Makes `filter-chain.service` startup distro-neutral: daemon reload, start/restart, retry after `reset-failed`, active-state verification, and final `soundblaster_zse_eq` sink verification now work on Fedora, Arch/CachyOS, and Bazzite when the unit exists.
- Fixes quoted WirePlumber `audio.position` parsing that could reject all six channel labels and silently regenerate `soundblaster_zse_eq` as stereo.
- Canonicalizes a complete logical 5.1 virtual EQ layout to `[ FL FR RL RR FC LFE ]` while allowing a corrected physical sink to advertise its own port order underneath.
- Adds an opt-in `--ca0132-channel-fix` installer switch for the community-verified Sound Blaster Z/CA0132 analog 5.1 physical map `[ FL FR FC LFE RL RR ]`; it remains opt-in until validated on more CA0132 systems.
- Preserves the v3.3.36 capability-driven activation of an available Sound Blaster analog 5.1 profile before EQ channel discovery.

## 3.3.36

- Adds capability-driven activation of `output:analog-surround-51` when a selected CA0132/Sound Blaster sink is stereo but its card explicitly exposes an available analog 5.1 profile. Existing surround-51 and AC3 targets are left unchanged.

## 3.3.35

- Hardens upgrades by backing up the active `state.json` before installer migration/normalization.
- Makes application state saves atomic and retains a last-known-good `state.json.backup-last` copy before replacement.
- Refuses to run the user-local installer itself as root/sudo, preventing accidental installation under `/root`.
- Documents that legacy state is only a fallback when no modern `state.json` exists.
- Adds Bazzite JamesDSP/WirePlumber stale-routing troubleshooting; JamesDSP is not required.
- Leaves the verified v3.3.34 Ubuntu/Bazzite DSP and channel-routing behavior unchanged.

## 3.3.34

- Fixes Bazzite Channel Levels by applying per-channel 0–100% attenuation to the selected physical multichannel sink, where the volume is in the verified live output path.
- Keeps Ubuntu on the existing verified `soundblaster_zse_eq` per-channel volume path; Ubuntu DSP, routing, Speaker Fill, Spatial, EQ, Safe Headroom, and meter behavior are unchanged.
- Startup restore/readback now verifies channel levels against the same distro-appropriate sink used for application.
- JamesDSP compatibility is not changed in this release; on Bazzite, JamesDSP must remain stopped while validating the Sound Blaster routing because its active nodes were observed to compete for FL/FR and Speaker Fill routes.

## 3.3.33

- UI-only fix: Speaker Fill LFE Crossover radio buttons now retain the dark card palette while disabled, with muted disabled text instead of the desktop theme's light fallback background.
- No DSP, routing, EQ, meter, Safe Headroom, or saved-state behavior changed.

## 3.3.33
- Replaces the shared six-channel Live Output recorder with six isolated mono `pw-record` streams, each explicitly linked to one physical AC3 `monitor_*` port.
- Keeps the spectrum analyzer sourced from those same verified physical outputs, eliminating the cross-feed seen with one interleaved recorder.
- Audio processing, EQ startup restore, Safe Headroom, Speaker Fill, Bass Management, and channel-volume behavior are unchanged.


- Live Output Levels and the spectrum analyzer now use one unconnected `pw-record --target=0` stream and explicitly `pw-link` each physical AC3 monitor port (`monitor_FL`, `monitor_FR`, `monitor_RL`, `monitor_RR`, `monitor_FC`, `monitor_LFE`) to the matching recorder input.
- Eliminates PipeWire target-node port guessing and Pulse channel remixing; verified stereo playback with Fill OFF reports only FL/FR while RL/RR/FC/LFE remain silent.
- Analyzer capture failures are surfaced in the GUI status line instead of being silently swallowed.
- Audio DSP/routing, v3.3.27 startup EQ restore, Safe Headroom, Speaker Fill, Bass Management, and 0-100% channel controls are unchanged.

## 3.3.29

- Live Output Levels now prefer the virtual EQ sink monitor instead of the physical AC3 encoder monitor.
- Removed semantic mono meter captures because Pulse/PipeWire can remix those requests and create phantom Center/LFE activity.
- Live meters are derived from one native multichannel EQ-monitor capture, then numerically reordered by the monitor's advertised channel map.
- Per-channel 0–100% attenuation remains folded into the displayed level so a muted channel reads silent.
- Audio routing, EQ startup restore, Safe Headroom, Speaker Fill, Bass Management, and channel controls are otherwise unchanged.

## 3.3.28

- Replaces LIVE OUTPUT LEVELS multichannel slicing with one explicit semantic mono monitor capture per speaker (`front-left`, `front-right`, `rear-left`, `rear-right`, `front-center`, `lfe`).
- Prevents Pulse/PipeWire capture remixing from creating phantom Center/LFE/rear activity when those output channels are actually silent.
- Retains the v3.3.27 first-start EQ restore fix, 0–100% channel controls, Safe Headroom, Speaker Fill DSP, Bass Management, and AC3 routing unchanged.
- Keeps the spectrum analyzer as a combined-output view; only the six discrete output meters use the new semantic capture path.

## 3.3.27

- Fixes first-launch EQ restore after install/upgrade by making saved `state.json` EQ values authoritative when regenerating the filter graph instead of inheriting a potentially stale pre-upgrade graph.
- Startup EQ restore now requires two consecutive matching live readbacks across a longer settling window before it reports success.
- Fixes LIVE OUTPUT LEVELS capture determinism by pinning `parec` to the monitor source's exact native channel count and exact native Pulse channel map, then reordering only numeric readings for the GUI.
- Fixes installer/version stamping that still reported 3.3.25 inside the 3.3.26 package.
- Leaves Safe Headroom, 0–100% channel controls, Speaker Fill DSP, Bass Management, and verified AC3 routing unchanged.

# v3.3.25

- Replaces per-speaker `-12..+12 dB` calibration trims with OS-style `0..100%` channel levels.
- Channel levels are attenuation-only: `100%` is unity/full volume and `0%` is mute; no per-channel boost is available.
- Existing <=v3.3.24 channel trims are migrated to the equivalent PipeWire/Pulse displayed percentage, with old positive boosts safely capped at 100%.
- Channel-level readback/restore verification now compares the same percentages shown by the operating system.
- Safe Headroom no longer treats speaker levels as possible positive gain because the new controls cannot exceed 100%.

# v3.3.24

- Fixes Ubuntu Speaker Fill OFF/PSD/FULL runtime synchronization by refreshing only `pipewire-pulse` when generated stream defaults change; newly-created stereo applications no longer inherit stale in-memory `channelmix` settings.
- Reasserts effective Safe Headroom, saved per-channel calibration, and the EQ default route after the targeted PipeWire-Pulse refresh.
- Fixes six-channel live meter capture to use the monitor source's native Pulse channel order, then maps meter values to GUI labels without asking `parec` to remix/reorder the monitored stream.
- Leaves the verified discrete 5.1 EQ graph, AC3 channel links, Bass Management DSP, and Bazzite behavior unchanged.

# v3.3.23

- Replaces the weak 20% redirected-bass gain with equal-power `1/sqrt(5)` summing, improving a single synthesized contribution by approximately 7 dB.
- Adds an Ubuntu-only final LFE look-ahead limiter at -0.5 dBFS to bound full-scale correlated main bass plus native LFE.
- Renames the separate Speaker Fill control to `Speaker Fill LFE Crossover` and disables it visually when fill is OFF without changing its DSP property or saved setting.
- Preserves Bass Management crossover/slope, native LFE Trim, Safe Headroom, EQ, trims, speaker mapping, AC3, and all Bazzite routing/service behavior.

# v3.3.22

- Implements real Ubuntu six-channel Bass Management with explicit main-channel HPF, redirected-bass LPF, native-LFE trim, and cross-channel LFE summing.
- Implements live OFF, REDIRECT, DUPLICATE, and LFE_ONLY routing plus measured 60–120 Hz crossover and 12/24 dB/oct filter behavior.
- Keeps LFE Fill Crossover separate in the existing Speaker Fill channelmix path.
- Leaves Bazzite on its verified duplicated EQ and persistent stereo-fill architecture.
- Adds routing, crossover, slope, native-LFE trim, graph-isolation, and no-leakage regression tests.

# v3.3.21

- Converts each saved channel-trim dB target to an absolute PulseAudio native-volume integer before issuing the six-channel `pactl set-sink-volume` command.
- Preserves independent per-channel dB verification and logs the exact argv, channel order, and requested targets.
- Adds regression coverage for the absolute 0 dB and -1 dB volume conversions.
- Retains v3.3.20 Safe Headroom and all routing, topology, speaker-test, distro, and Bazzite behavior unchanged.

# v3.3.20

- Preserves the saved current EQ curve through `load_data()` so Safe Headroom startup calculations use the restored EQ and preamp settings.
- Adds state round-trip regression coverage for boosted and flat EQ curves and for Safe Headroom disabled.
- Retains the v3.3.19 verified `preamp:Mult` write/readback/retry behavior without changing other audio paths.

# v3.3.19

- Applies the calculated Safe Headroom target to live `preamp:Mult` on every GUI startup and verifies it through bounded write/readback settling retries.
- Uses the same verified helper for login `--restore`.
- Logs the target multiplier, every write and readback, and final success or failure to `restore.log`.
- Reports actual live attenuation in the GUI when startup verification fails.
- Does not change speaker testing, Speaker Fill, EQ topology, AC3 routing, distro branching, or channel-level behavior.

# v3.3.18

- Uses the hardware-verified fixed `speaker-test` selection map on Ubuntu Pulse: FL=1, FC=2, FR=3, RR=4, RL=5, LFE=6.
- Makes the Ubuntu bass/LFE test explicitly select speaker 6.
- Keeps Bazzite speaker-test mapping and all routing, Speaker Fill, EQ, Safe Headroom, installer, and AC3 behavior unchanged.

# v3.3.17

- Restores Ubuntu Speaker Fill to the v3.3.2 global PipeWire-Pulse channelmix implementation; Ubuntu no longer creates `soundblaster_zse_fill`, runs `pw-loopback`, or moves streams every 1.5 seconds.
- Keeps Bazzite on the verified v3.3.15 persistent stereo-fill architecture, including in-place OFF/PSD/FULL changes, discrete native multichannel playback, and stable Vivaldi playback.
- Restores Ubuntu speaker tests to the v3.3.2 physical AC3 sink, fixed `pulse` backend, detected channel-map numbering, and `-t sine`; Bazzite's verified PipeWire mapping is unchanged.
- Applies per-channel calibration with explicit dB values and verifies dB readback with bounded retries.
- Adds live `preamp:Mult` readback and bounded startup reapplication so Safe Headroom survives session startup resets.
- Shows the calculated Safe Headroom target separately from the actual live preamp attenuation.

# v3.3.16

- Fixes normal GUI startup so saved per-channel calibration is actually re-applied to the live `soundblaster_zse_eq` sink and verified with bounded readback, not merely loaded into the sliders.
- Fixes Safe Headroom startup: the effective safe preamp is asserted immediately on GUI launch instead of waiting for the checkbox to be toggled.
- Fixes preamp persistence by updating the PipeWire preamp node's `Mult` control (the old code incorrectly searched for `Gain 1`).
- When EQ config must be generated/rebuilt, writes the effective Safe Headroom preamp rather than the unsafe requested preamp.
- Spatial OFF/PSD/FULL changes now re-assert Safe Headroom and saved channel trims after routing changes so Speaker Fill cannot leave the EQ sink at unity.
- Preserves the v3.3.15 persistent stereo-fill architecture: stereo stays on one stable fill sink, while native multichannel bypasses it and remains discrete.
- Ubuntu continues to use the working ALSA `pulse` speaker-test backend when `pipewire` PCM is unavailable; Bazzite keeps its verified PipeWire channel numbering.

# v3.3.15

- Keeps the stereo Speaker Fill virtual sink persistent across OFF, PSD, and FULL.
- Changes channelmix properties on the existing fill playback node in-place with `pw-cli set-param`, avoiding active application sink moves when toggling modes.
- OFF leaves stereo applications on the same 2-channel virtual sink but disables upmix, so only FL/FR are produced; PSD/FULL enable the 2-to-6 upmix on that same route.
- Native 5.1/7.1 streams continue to bypass the stereo fill sink and remain discrete.
- Newly-created stereo streams are still routed to the persistent fill sink; this one initial route is unavoidable, but subsequent mode changes do not reconnect the application stream.

# v3.3.14

- Replaces the ineffective PipeWire-Pulse `stream.rules` stereo match with a dedicated stereo-only Speaker Fill sink built with `pw-loopback`.
- Stereo applications are routed to `soundblaster_zse_fill` (2-channel input), upmixed there to FL/FR/RL/RR/FC/LFE, then sent through the existing 5.1 EQ sink.
- Native multichannel streams stay on `soundblaster_zse_eq` and are never remixed by Speaker Fill.
- Speaker Fill OFF moves filled streams back to the normal EQ route and stops only the fill loopback; PipeWire/WirePlumber are never restarted.
- A lightweight routing check catches newly-created stereo streams while the GUI is open without disturbing native 5.1 playback.
- Preserves the v3.3.12 Bazzite speaker-test mapping, EQ, channel trims, AC3 route, and Ubuntu-specific behavior.

## 3.3.26

- Flipped Channel Levels to the conventional 0% left → 100% right direction.
- Fixed LIVE OUTPUT LEVELS so the meters follow the final 0–100% per-channel sink attenuation, including a true meter drop when a channel is set to 0%.
- Stopped `parec` from requesting/remapping a channel map for analyzer capture; native monitor order is detected and only the displayed numeric levels are reordered.
- Normal GUI startup now reapplies and verifies the saved 10-band EQ, so the selected preset is active without reselecting it after every launch.

## 3.3.13

- Speaker Fill is now stereo-only: native multichannel streams are left discrete.
- Replaces the old global `channelmix.upmix=true` behavior with a two-channel `stream.rules` match.
- Live Speaker Fill updates enable upmix only on streams explicitly reporting two channels.
- Installer migrates existing 3.3.x Speaker Fill configuration while preserving the selected fill mode, delay, width, cutoff, EQ, and channel trims.
- Keeps the verified Bazzite speaker-test mapping and Ubuntu path from 3.3.12 unchanged.

## 3.3.12

- Corrected per-speaker test selection for the Fedora/Bazzite PipeWire ALSA PCM using the hardware-verified 5.1 selection map: FL=1, FR=3, RL=5, RR=4, FC=2, LFE=6.
- Preserved the existing Ubuntu/pulse speaker-test numbering unchanged.
- No PipeWire audio-position remapping, EQ routing, channel-level processing, or saved settings were changed.

# 3.3.12

- Fixes per-speaker test selection by using speaker-test's documented fixed channel numbering instead of indexing the PipeWire channel-position array.
- Keeps the capability-detected speaker-test backend from 3.3.10 (`pipewire` preferred, then `pulse`, then `default`).
- Corrects the LFE-only bass test to target speaker-test channel 6 for 5.1.
- Does not alter the physical AC3 default route or saved EQ/channel settings.

# 3.3.10

- Restores the physical AC3 5.1 sink as the normal/default route on Bazzite, matching the working Ubuntu architecture.
- Speaker and bass tests now select the installed ALSA PipeWire PCM when available, falling back to pulse/default instead of hardcoding `-D pulse`.
- Removes v3.3.9 forced virtual-EQ default routing and stream moves.

# 3.3.10

- Bazzite routing authority correction: when the EQ sink is healthy, `soundblaster_zse_eq` is the system default; the physical AC3 sink is fallback only.
- Existing playback streams are moved to the EQ route when the route is activated, so already-running games/media do not bypass processing.
- Speaker and bass test tones explicitly target `soundblaster_zse_eq` via `PULSE_SINK` and no longer switch the default sink back to the physical device.
- Preserves the confirmed channel map `FL FR RL RR FC LFE`; no distro-specific channel reordering is introduced.

- Fixed Bazzite installer abort caused by the mismatched `IS_BAZZITE`/`is_bazzite` variable.
- Distribution/platform detection and dependency validation complete before backup or replacement begins.
- Retains the v3.3.7 safety rule: missing EQ never triggers automatic PipeWire/WirePlumber restarts.

- Safety/stability: removed periodic automatic audio-stack recovery when the EQ node is missing.
- Bazzite now remains on the verified physical AC3 5.1 sink without interruption when EQ is unavailable.
- Added manual Retry EQ; Bazzite retry affects only filter-chain.service.
- Connection status distinguishes EQ failure from hardware-output failure.
- No automatic PipeWire/WirePlumber restart is performed by the status poller.

# 3.3.6

- Bazzite/Fedora 44: launch the EQ through PipeWire's packaged `filter-chain.service` instead of repeatedly restarting the whole PipeWire/WirePlumber stack.
- Correct the multichannel EQ graph: the one-channel DSP graph is now duplicated by PipeWire across the active 2/6-channel stream instead of declaring one graph port for a six-channel stream.
- Master preamp now uses PipeWire's builtin linear filter (`Mult`) so it remains one-input/one-output and is safe for graph duplication.
- Keep AC3 5.1 hardware targeting and user-local Atomic installation behavior from 3.3.5.

# 3.3.5

- Bazzite/Fedora Atomic: automatically prefer the advertised Sound Blaster AC3 5.1 profile while preserving analog input.
- Bazzite compatibility routing uses a conventional PipeWire virtual filter sink when smart-filter insertion is unavailable.
- PipeWire restart verification now waits for both the physical target and EQ node and reports the actual missing component.
- Avoids redundant/false restart failures and uses the EQ sink as the default route in Bazzite compatibility mode.

# 3.3.5

- Fixes Bazzite/Fedora Atomic dependency detection for `alsa-plugins-a52`: an installed/layered RPM is now accepted even when `aplay -L` does not enumerate an `a52` PCM.
- Keeps runtime `a52` enumeration for mutable distributions while using RPM package state as an additional authoritative signal on Bazzite.
- Streamlines Atomic setup by presenting all genuinely missing host dependencies in one `sudo rpm-ostree install ...` transaction followed by a single reboot.
- Application files remain user-local; no attempt is made to bundle or overwrite host PipeWire/ALSA components.
- Retains the v3.3.3 bounded channel-level restore/readback fix unchanged.

# 3.3.3

- Fixes intermittent per-channel level restoration after login/reboot with verified, bounded re-application after the PipeWire virtual sink becomes ready.
- Adds concise restore diagnostics at `~/.config/soundblaster-zse-control/restore.log` without overwriting saved channel settings from transient runtime values.
- Keeps EQ/preamp behavior unchanged and preserves existing user state during upgrades.
- Confirms the application/launcher/autostart install remains entirely user-local under `~/.local` for Bazzite/Fedora Atomic compatibility; the installer does not write application files to `/usr/local`.
- Corrects installer state-version stamping to the current release.

# 3.3.2

- Audited distributable for machine-specific/private identifiers.
- Added !!ZuEs!! contact email to the Device Setup / Package & System signature area.
- Cleaned public README branding/version and documented portability/privacy audit.
- No playback, EQ, DSP, microphone-processing, or routing behavior changed.

# 3.3.0

- Added distribution-aware installer support for Debian/Ubuntu family, Fedora, Arch/Manjaro/EndeavourOS, and Bazzite/Fedora Atomic.
- Bazzite/Atomic installs never auto-layer missing host packages; the installer reports what is missing and exits safely.
- Preserves the confirmed 3.2.1 UI, playback DSP, microphone EQ and noise-reduction behavior.

# 3.2.1

- Added optional Sound Blaster Processed Mic virtual source.
- Added live 3-band microphone EQ (160 Hz, 1.8 kHz, 6 kHz).
- Added adjustable low-level background-noise reduction using PipeWire built-in noise gate.
- Preserved the physical microphone and existing 3.2.0 playback/EQ path.
- Corrected installer/state version reporting to 3.2.1.

# 3.2.0

- Line Input tab now exposes the physical input port selector alongside persistent Input Level and Mic Boost controls.
- Added 0-100% capture level and 0 to +30 dB software microphone boost.
- Input gain settings are saved and restored without changing the working playback DSP path.

# 3.1.9

- Replaced low-visibility native sliders with high-contrast custom blue-track controls and bright handles across EQ, preamp, calibration, Spatial/Fill, and bass controls.


- Refined all EQ, preamp, channel, spatial, and bass-management sliders with slimmer dark tracks and compact bright-blue thumbs to match the redesigned interface.
- UI-only revision; audio routing and DSP behavior are unchanged.

# 3.1.5
- Increased default application window height by another 40 pixels so the bottom status bar is visible without manually expanding the window.

# 3.1.3

- Reworked EQ & Levels layout to fit at the default window size without maximizing.
- Moved the spectrum analyzer directly under the 10-band EQ to use the large empty area efficiently.
- Kept all speaker calibration controls together in the right column.
- Reduced the signature footprint and placed it in otherwise-unused lower-right space.
- Reduced excess padding/slider height while preserving all working controls and audio behavior.

# 2.5.2

- Added optional Bass Management controls.
- Added bass test tones.
- Preserved 2.4.0 routing by keeping Bass Management disabled by default.

## 3.1.9
- Unified all LabelFrame/content backgrounds with the dark concept theme.
- Corrected the ttk Labelframe style name so KDE/GNOME no longer fall back to a light system panel background.
- Increased text and border contrast while retaining the 3.1.7 high-visibility blue sliders.
- No audio, routing, DSP, preset, or device behavior changes.

## 3.3.2
- Expanded README with a basic quick-start installation section.
- Added standalone TROUBLESHOOTING.md covering routing, 5.1 optical, device profiles, analyzer, speaker test, Mic/Line In, processed microphone, line monitoring, dependencies, and bug-report diagnostics.


## 3.3.68-test4 (unreleased)
- Manual Use Sound Blaster fallback, vendor-neutral audio handoff, passive EQ restore on return, experimental analog >2.1 labeling. See RELEASE_TEST_NOTES.md.

## 3.3.68-test4 (unreleased)
- Detect device routing changes without relying on default sink changes; restore existing SBLCC speaker-fill routing with GUI closed.
