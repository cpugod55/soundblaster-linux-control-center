## v3.3.38

This release fixes a remaining case where a real analog 5.1 Sound Blaster sink could be regenerated as a 2.0 EQ sink after reboot. The installer and application now prefer the real `Audio/Sink` entry when PipeWire exposes duplicate matching objects, and `analog-surround-51` targets are protected from transient stereo fallback.

## 3.3.38

- Arch/CachyOS and Fedora now install the correct ZaMaxim LADSPA package automatically on mutable systems; Bazzite/Fedora Atomic reports the package for host layering.
- Existing root-owned `~/.config/pipewire` directories are detected before writes. Use the installer-provided `chown` command, then rerun `./install.sh` without sudo.
- `filter-chain.service` is started and verified on any distro that provides the user unit.
- A valid quoted six-channel WirePlumber map no longer collapses the generated EQ sink to 2.0.
- The CA0132 analog channel-map correction is available only when explicitly requested with `--ca0132-channel-fix`; existing manual WirePlumber corrections are left untouched.

## 3.3.35

Bazzite Channel Levels now target the saved physical 5.1/AC3 sink instead of the virtual `soundblaster_zse_eq` sink. Manual testing showed Bazzite accepted virtual-sink per-channel volume readback but did not attenuate the actual output; applying the same six values to the physical sink correctly muted the selected speaker. Ubuntu keeps the existing v3.3.33 channel-level path unchanged.

For Bazzite validation, keep JamesDSP stopped for now. Its PipeWire nodes were observed attaching to the physical FL/FR outputs and intercepting Speaker Fill, which caused incorrect rear-channel and Spatial behavior independently of this Channel Levels fix.

## 3.3.33

UI-only update from the verified 3.3.32 baseline. The disabled Speaker Fill LFE Crossover choices now use an explicit dark ttk style so they match the rest of the Spatial / Fill panel. Audio processing is unchanged.

## 3.3.33

This release changes only visualization capture. The meter/analyzer recorder is created with `pw-record --target=0`, then the app explicitly links each physical Sound Blaster AC3 monitor port to the matching recorder input with `pw-link`. This matches the verified manual diagnostic where stereo + Fill OFF produced signal on FL/FR only and digital silence on RL/RR/FC/LFE. Audio routing and DSP behavior are unchanged.

## 3.3.29

This release changes only the Live Output Level measurement path. The app now measures the native multichannel `soundblaster_zse_eq.monitor` stream before AC3 encoding and maps those samples to channel labels without asking Pulse/PipeWire to create mono remixes. This is intended to make silent Center/LFE/rear channels remain visually silent when they are not actually carrying audio.

## 3.3.28

LIVE OUTPUT LEVELS now measure each named output channel independently instead of inferring channel identity from a remixed multichannel `parec` capture. This specifically fixes phantom activity on Center, LFE, and rear meters during stereo playback with Speaker Fill off. No EQ, Safe Headroom, Speaker Fill, Bass Management, or routing behavior changes in this release.

## 3.3.27

This release targets two remaining startup/visualization issues from 3.3.26. The saved EQ curve is now the authoritative source when the installer regenerates the PipeWire filter graph, and GUI startup waits for two consecutive verified live EQ readbacks before declaring the curve restored. LIVE OUTPUT LEVELS now captures the physical/EQ monitor with its exact native channel count and native Pulse channel map so the byte layout parsed by the meters is deterministic.

Safe Headroom, Speaker Fill behavior, Bass Management, AC3 routing, and OS-style 0–100% channel levels are otherwise unchanged.

## 3.3.26

Speaker/channel calibration now uses 0-100% levels matching PipeWire/Pulse system volume. Existing attenuation is converted automatically; legacy boosts above 0 dB become 100%.

## 3.3.24

- Fixes Ubuntu Speaker Fill runtime synchronization: when the generated PipeWire-Pulse stream defaults change, the app refreshes only `pipewire-pulse` so newly-created stereo streams cannot inherit stale `channelmix.upmix=true` / `simple` settings after Speaker Fill is OFF.
- Reasserts Safe Headroom, saved channel calibration, and the EQ route after that targeted refresh.
- Fixes live six-channel meters to capture the monitor source in its native channel order and reorder only numeric meter values for display, preventing `parec` from remapping the monitor during measurement.
- Preserves the verified discrete 5.1 EQ/AC3 graph and Bazzite routing behavior.

## 3.3.23

Ubuntu REDIRECT/DUPLICATE bass synthesis now uses equal-power summing and a final LFE overload limiter. The renamed Speaker Fill LFE Crossover remains the existing Speaker Fill-only control. Ubuntu installs `zam-plugins` when its limiter is unavailable; Bazzite dependencies and services are unchanged.

## 3.3.22

Ubuntu 5.1 Bass Management controls now drive an explicit cross-channel DSP graph. Install once to create the new graph; subsequent mode, crossover, slope, and native-LFE trim changes apply live and persist. Bazzite Speaker Fill/EQ routing and the separate LFE Fill Crossover are unchanged.

## 3.3.21

Per-channel restoration now uses absolute PulseAudio native-volume values, avoiding pactl's conflicting relative negative-dB syntax while retaining exact dB readback verification. Safe Headroom and Ubuntu/Bazzite routing behavior are unchanged.

## 3.3.20

Safe Headroom startup now restores the saved current EQ curve before calculating and verifying the live preamp multiplier. Speaker Fill, speaker mapping, EQ topology, routing, and channel calibration are unchanged.

## 3.3.19

Safe Headroom is now considered restored only after live `preamp:Mult` readback remains at the calculated target through startup settling. Failure diagnostics include the actual live attenuation.

## 3.3.18

Ubuntu speaker tests now use the hardware-verified fixed ALSA speaker numbering instead of deriving `-s` from PipeWire's channel-map order. Bazzite behavior is unchanged.

## 3.3.17

Ubuntu returns to the verified v3.3.2 Pulse speaker-test and global Speaker Fill paths. Bazzite retains the v3.3.15 persistent fill sink and PipeWire speaker mapping. Saved channel calibration and Safe Headroom are re-applied with bounded live readback after startup.

## 3.3.16

Speaker Fill now keeps one stable stereo virtual sink across OFF/PSD/FULL and changes the fill processing in-place. This is intended to prevent browsers such as Vivaldi from pausing video when Speaker Fill is toggled. Existing EQ, channel trims, spatial settings, AC3 routing, and native multichannel behavior are preserved.

## 3.3.14

Upgrading from 3.3.12 automatically replaces the global Speaker Fill drop-in with a stereo-only rule. Existing EQ bands, channel trims, Speaker Fill mode, rear delay, stereo width, and LFE cutoff are preserved. Native 5.1/7.1 streams are no longer intentionally upmixed.

## 3.3.12

Upgrade directly over 3.3.10. The speaker-test buttons now use speaker-test's fixed speaker numbering (FL, FR, RL, RR, FC, LFE) rather than treating PipeWire audio.position as speaker-test numbering. The physical AC3 5.1 sink remains the normal/default route and existing settings are preserved.

## 3.3.10

Upgrade directly over 3.3.9. Bazzite returns to the physical AC3 5.1 sink as the default output. Speaker tests use a capability-detected ALSA backend (`pipewire` preferred, then `pulse`, then `default`). Existing settings are preserved.

## 3.3.10

Upgrade directly over 3.3.8. Existing EQ, channel, preset, and device settings are preserved. On Bazzite, a healthy EQ route becomes the default and currently playing Pulse/PipeWire streams are moved to it. The physical AC3 5.1 sink remains the fallback when EQ is unavailable. Speaker-test buttons now explicitly target the EQ route and do not change the system default.

Upgrade directly over 3.3.6. Existing EQ, channel, preset, and device settings are preserved. The previous automatic reconnect preference is retained in settings for compatibility but is no longer allowed to trigger periodic recovery. Use Retry EQ manually if the optional EQ node is unavailable.

## 3.3.6

On Bazzite/Fedora 44 the installer enables the PipeWire-provided `filter-chain.service`. No additional host package is required when the standard PipeWire package is present. Existing settings and EQ gains are preserved.

## 3.1.9

UI-only slider styling update. Existing audio settings and routing are preserved.

# Upgrade Notes — 2.4.0

Master Preamp is now a persistent global gain control and is no longer stored or recalled by EQ presets. Existing custom presets remain compatible; any legacy `preamp` field in them is simply ignored. The default window is also 20 pixels taller.

# Upgrade notes for 2.3.0

Run `./install.sh` from this package over 2.2.0.

The installer makes timestamped backups and preserves:

- all 10 EQ band values
- per-channel FL/FR/RL/RR/FC/LFE trims
- custom presets
- spatial/fill settings
- the selected physical Sound Blaster target

For installs whose saved state reports version 2.2.0, the Master Preamp is reset to **0.0 dB** because 2.2.0 used a defective gain method on the smart-filter AC3 path. Safe Headroom is not forced on or off; your saved setting is preserved.

In 2.3.0 the Master Preamp is a DSP gain stage inside the filter graph. Safe Headroom no longer changes the slider value; it applies a separate effective ceiling. The clipping/headroom warning now has its own full-width row.

## 2.3.0 UI upgrade

This upgrade does not change the 2.2.x smart-filter audio routing or DSP graph. It adds preset-selection indicators, main-page custom preset recall, and an optional spectrum analyzer. Existing custom presets and current EQ/channel values are preserved.

## 3.2.0
Existing 3.1.9 playback, EQ, spectrum, channel-meter, spatial, and bass-management settings are preserved. New input gain settings default to 100% level and 0 dB boost.


## 3.3.0

Installer portability update only. Audio/DSP and the 3.2.1 interface are intentionally unchanged.


## 3.3.2

Public-distribution audit release. No audio behavior changes. The Package / System area now shows the !!ZuEs!! contact address.

## 3.3.3

Existing EQ, channel trims, presets, and device selection are preserved. Login restore now verifies channel-volume readback and uses bounded retries to survive PipeWire/WirePlumber startup resets. Bazzite/Fedora Atomic application files remain user-local under `~/.local`.


## 3.3.5

Bazzite/Fedora Atomic dependency detection now recognizes an installed `alsa-plugins-a52` RPM even if ALSA runtime enumeration does not list an `a52` PCM. Missing Atomic host dependencies are grouped into one rpm-ostree transaction. Channel restore behavior is unchanged from 3.3.3.

### State safety in 3.3.35

Run `./install.sh` as the normal desktop user, **not** with `sudo`. The installer now refuses root execution. Before migration/normalization, an existing `~/.config/soundblaster-zse-control/state.json` is copied to a timestamped `state.json.backup-YYYYMMDD-HHMMSS` recovery file. The application also writes state atomically and keeps `state.json.backup-last` as the previous state.

If no modern `state.json` exists but `~/.config/soundblaster-zse-control.json` does, that legacy file remains a fallback migration source. It is not allowed to overwrite an existing modern state.

### Bazzite / JamesDSP compatibility

JamesDSP is not required. If JamesDSP was previously installed or used, WirePlumber can retain stream targets pointing at `jamesdsp_sink` even after Sound Blaster routing is otherwise correct. Symptoms can include wrong Rear Left/Rear Right speaker tests, Spatial or Speaker Fill not behaving correctly, or unexpected routing. If JamesDSP was installed only while troubleshooting Sound Blaster audio, removing it is recommended. Restart the user PipeWire/WirePlumber session afterward and reopen Sound Blaster Linux Control Center. If symptoms remain, inspect `~/.local/state/wireplumber/stream-properties` for stale `jamesdsp_sink` targets before changing Sound Blaster DSP configuration.
