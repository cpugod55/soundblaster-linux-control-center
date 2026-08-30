## **3.3.36**

- Add capability-driven Sound Blaster analog 5.1 profile activation for compatible CA0132 devices.
- Improve multichannel detection when PipeWire initially selects an analog stereo profile.
- Add regression coverage for 5.1 profile activation and existing surround/AC3 sink preservation.
- Add GitHub Sponsors funding configuration and project support information.

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
