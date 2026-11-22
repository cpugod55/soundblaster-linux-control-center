## 3.3.65
After an Output Setup change, the relaunched app now visibly reports that audio is settling and temporarily disables another Apply action for 4.5 seconds. This prevents the rapid repeated-change race observed in v3.3.64 while keeping the persistent relaunch helper design.

## 3.3.65

Output Setup now uses a persistent user-session relaunch helper. The installer enables `soundblaster-zse-relaunch-helper.service` automatically; no manual service setup is required. This replaces the unsuccessful v3.3.63 terminal/`gtk-launch` relaunch path and is intended to support repeated speaker-layout or connection changes in one desktop session.

## 3.3.53 openSUSE + Debian installer validation fixes

openSUSE Tumbleweed now has a dedicated `zypper` path and can create the persistent Creative Digital AC3 sink from `plug:a52:<card>`. This was selected because openSUSE's `alsa-plugins-a52` PCM works directly even when `aplay -L` does not list an A52 hint. The installer also unmutes both IEC958 playback controls when present.

Debian clean-Live installs now bring up the user PipeWire audio stack before `pactl` hardware detection and fail with an explicit diagnostic if the Pulse compatibility server is still unavailable. No DSP or routing behavior from v3.3.52 is intentionally changed.

## 3.3.52 Ubuntu explicit Speaker Fill test

This test build applies the v3.3.51 explicit Speaker Fill graph to Ubuntu's native Creative AC3 5.1 sink (`iec958-ac3-surround-51`) so its sound can be compared directly with the Linux Mint result before additional distro validation. The main EQ graph and Ubuntu native AC3 target selection are not converted to A52 compatibility mode. Bazzite remains unchanged.

## 3.3.52 explicit A52 Speaker Fill DSP + UI family refresh

## v3.3.52

Mint/A52 Bass Management now rebuilds only the Sound Blaster filter-chain graph so crossover, slope, routing, and LFE trim are creation-time DSP values. The persistent A52 hardware sink remains intact. Speaker Fill topology is unchanged from the verified v3.3.50 implementation. UI accent is blue again.


Linux Mint 22.3 proved that the v3.3.49 recreation workaround was executing: `soundblaster_zse_fill_output` was destroyed and recreated with new object IDs/serials when Fill changed, yet the speakers still sounded unchanged. v3.3.52 therefore stops depending on PipeWire channelmix for non-Atomic A52 routing. Stereo applications enter a dedicated two-channel virtual sink and the application-owned filter graph explicitly generates canonical FL/FR/RL/RR/FC/LFE before the main EQ. OFF sends only front stereo, PSD derives difference ambience for the rear pair, FULL duplicates left/right to the rears, Center is synthesized from L+R, LFE is synthesized through the selected low-pass, and Rear Delay/Stereo Width are graph controls.

The first v3.3.52 launch also removes the old named Fill `pw-loopback` left by earlier versions before the new graph is loaded. Bazzite keeps its already-verified compatibility path. This build also moves the Sound Blaster UI closer to the AMD Linux Control Center visual family while preserving the v3.3.49 privacy-safe About links.

## 3.3.49

The Package / System page no longer exposes the maintainer email address. Project contact is through GitHub Issues, and the app includes GitHub Project and Support / Sponsor buttons. Audio/DSP behavior is unchanged from 3.3.48.

## v3.3.48 Mint / older PipeWire Fill recreation compatibility

Mint 22.3 proved the GUI-to-PipeWire path was working: OFF changed `channelmix.upmix` to false, while FULL changed it to true with `channelmix.upmix-method=simple` on the correct `soundblaster_zse_fill_output` node. The audible DSP still did not change. v3.3.48 therefore recreates only the dedicated Fill loopback on PipeWire < 1.2 when a Fill parameter changes, placing the requested DSP settings on the stream at creation time. Newer Fedora/CachyOS behavior remains live/in-place. The Cinnamon busy-cursor launcher quirk is also corrected.

## v3.3.48 A52 Spatial / Bass Management fix

Linux Mint runtime testing showed that v3.3.46 restored the first-tab meters/analyzer and GUI responsiveness, while second-tab controls changed visually without changing audio. The persistent A52 Fill loopback was created with `stream.dont-remix=true` even though that same stream relies on PipeWire channelmix to expand stereo to 5.1. v3.3.48 allows remixing on that stream so OFF/PSD/FULL, Rear Delay, Stereo Width, and Speaker Fill LFE Crossover can take effect. It also keeps the explicit six-channel Bass Management graph active on non-Bazzite A52 compatibility targets and preserves direct `target.object` routing when Bass Management settings are persisted. Bazzite's verified compatibility graph remains unchanged.

## v3.3.46 Linux Mint runtime compatibility

Linux Mint 22.3 validated the v3.3.45 A52/AC3 installer and audio graph, but exposed two application-runtime compatibility issues: its `pw-record` build does not implement `--raw`, leaving Live Output Levels and the spectrum analyzer blank, and synchronous dedicated Fill-route maintenance in the Tk status poll could make the GUI controls unresponsive. v3.3.46 capability-detects `pw-record --raw`, keeps isolated physical monitor-port metering on compatible syntax, and moves periodic dedicated Fill routing to a background worker protected by a route lock.

## v3.3.45 Linux Mint / Debian-family Digital 5.1

Linux Mint 22.3 Live validation showed that the Creative CA0132 card exposed Digital Stereo IEC958 but no native AC3 5.1 PipeWire profile. The installed `libasound2-plugins` A52 encoder worked correctly once the Creative IEC958 playback switch was enabled. v3.3.46 generalizes the persistent A52 path to Debian/Ubuntu/Mint while preserving a native Creative AC3 profile when one is available.

Explicit Digital 5.1 requests now fail closed rather than silently selecting another audio device. Mint Live systems with a stale `deb cdrom:` APT source are handled automatically after an initial `apt-get update` failure, with the edited source file backed up before the stale entry is disabled.

## v3.3.44 Fedora Digital 5.1

- Fedora non-Atomic installs now create `alsa_output.soundblaster_a52_51` for explicit Digital 5.1 when `alsa-plugins-a52` is available.
- Creative IEC958 ALSA card/device numbers are discovered dynamically; no Fedora card number is hard-coded.
- The installer enables the Creative `IEC958` playback switch when that mixer control exists, then releases the normal ACP profile so A52 can own the S/PDIF PCM.
- Bazzite remains on its existing Atomic-host handling.
- v3.3.43 remains the verified CachyOS rollback checkpoint.

## v3.3.43 CachyOS / Arch Digital 5.1 Speaker Fill
- v3.3.42 proved optical AC3 5.1 playback, but changing Speaker Fill could restart `pipewire-pulse`, recreate the A52 sink, and strand the active desktop audio stream.
- v3.3.43 keeps the A52 sink alive and changes OFF/PSD/FULL in-place through a persistent stereo fill route.
- No System Settings output re-selection should be needed when changing Fill.

## v3.3.42 CachyOS / Arch Digital 5.1

When Digital + 5.1 is selected, the installer temporarily disables the normal Creative ACP card profile so the A52 encoder can exclusively open the same IEC958 hardware PCM. The A52 sink remains the active owner on success. If creation fails, the previous Creative profile is restored.

## v3.3.39

This release closes the remaining upgrade-path stereo fallback seen on gjohnz's v3.3.38 system. When an older EQ graph preserved an `analog-stereo` target but the exact same device is now exposing a live `analog-surround-51` sink, the installer and direct EQ-config generator now follow that live 5.1 sibling before regenerating the graph. Existing surround/AC3 targets, unrelated stereo devices, Bazzite routing, and the opt-in CA0132 physical channel-order correction are unchanged.

## 3.3.38 changes retained in 3.3.39

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
