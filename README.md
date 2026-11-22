# Sound Blaster Linux Control Center v3.3.7 — Community Testing Pre-release

**v3.3.7 is the public-facing name of the hardware-tested v3.3.68-test4 checkpoint.** The name is intentional; it is not an older codebase. This is a **pre-release**, not a fully cross-distribution-verified stable release.

**Verified:** Ubuntu 26.04 KDE on a Sound Blaster Z-series CA0132 using digital AC3 5.1 and an external surround speaker system. Automatic switching to a headset and back restores 5.1 and EQ with the GUI closed, after roughly 1–2 seconds, in the maintainer's hardware test.

**Not yet validated:** this exact build on Fedora, Bazzite, CachyOS, Mint, Debian, and openSUSE or on every supported Creative model. Device detection and capabilities differ; analog layouts above 2.1 are **EXPERIMENTAL**, and CA0132 analog multichannel routing may be unreliable.

**Install (from extracted archive, as the desktop user, without sudo):**

```bash
./verify_package.sh
./install.sh
```

**Rollback:** stop the optional background helper with `systemctl --user disable --now soundblaster-zse-audio-return.service`, then reinstall your previously working SBLCC release. Read `RELEASE_NOTES_v3.3.7.md` before upgrading.

---

## Support the project

If Sound Blaster Linux Control Center is useful to you, you can support continued development through GitHub Sponsors.

The repository includes a GitHub funding configuration so the **Sponsor** option can be displayed when GitHub Sponsors is enabled for the maintainer account.

# Sound Blaster Linux Control Center 3.3.53

## 3.3.53 current test build


openSUSE Tumbleweed test focus: add native `zypper` dependency handling and a persistent Creative Digital A52 fallback using openSUSE's verified `plug:a52:<card>` PCM. The installer enables the Creative `IEC958` and `IEC958 Default PCM` playback switches when exposed. `aplay -L` enumeration is not required for this path.

Debian clean-Live handling now starts the user PipeWire/WirePlumber/PipeWire-Pulse stack before hardware detection when `pactl` cannot connect, reports a clear error instead of silently exiting under `set -e`, and deduplicates repeated package names.

Ubuntu test focus: use the v3.3.51 explicit Speaker Fill DSP on native Creative AC3 5.1 without changing the established Ubuntu EQ target path.

Linux Mint / non-Atomic A52 Digital 5.1 now uses an explicit application-owned stereo-to-5.1 PipeWire filter graph for Speaker Fill instead of relying on PipeWire channelmix. The graph owns OFF/PSD/FULL, rear delay, stereo width, Center synthesis, and Speaker Fill LFE low-pass while preserving canonical `FL FR RL RR FC LFE` channel identity into the main EQ. Bazzite keeps its previously verified compatibility path.

The interface also adopts the same visual family direction as AMD Linux Control Center: darker neutral cards, red accent controls, and a dashboard-style connection/version header.


## 3.3.39 stale-target 5.1 upgrade fix

3.3.39 keeps the verified 3.3.38 cross-distro and CA0132 fixes and closes one remaining upgrade-path hole: if an older EQ graph preserved an `analog-stereo` target while the exact same device is currently exposing a live `analog-surround-51` sink, installation/config regeneration now follows that live 5.1 sibling instead of recreating a 2-channel `soundblaster_zse_eq` sink.

A community-verified CA0132 analog 5.1 hardware-port correction is available with `./install.sh --ca0132-channel-fix`. The option is deliberately opt-in while additional CA0132 machines are tested. The virtual EQ remains canonical `[ FL FR RL RR FC LFE ]`; the physical correction underneath is `[ FL FR FC LFE RL RR ]`.

## 3.3.24 REDIRECT level and LFE overload protection

Ubuntu Bass Management now uses equal-power `1/sqrt(5)` gain per synthesized main-channel contribution instead of 20%. This improves a single redirected channel by about 7 dB and places five uncorrelated contributions at unity RMS. An Ubuntu-only look-ahead limiter caps the final native-plus-synthesized LFE output at -0.5 dBFS for correlated overloads. Speaker Fill LFE Crossover is now clearly named in the Spatial/Speaker Fill panel and is disabled visually while Speaker Fill is OFF; its saved key, range, and `channelmix.lfe-cutoff` behavior are unchanged.

## 3.3.22 real Ubuntu Bass Management

Ubuntu 5.1 now uses an explicit six-channel DSP graph: Safe Headroom and EQ feed selectable full-range or 12/24 dB/oct high-passed main outputs, while matched low-pass branches can be summed into LFE. Native LFE has its own trim before the sum. `REDIRECT`, `DUPLICATE`, `LFE_ONLY`, and OFF update live without changing channel identity.

Bazzite retains its verified duplicated mono EQ and persistent stereo Speaker Fill architecture. LFE Fill Crossover remains the separate `channelmix.lfe-cutoff` Speaker Fill control.

## 3.3.21 exact channel-trim restoration

Saved six-channel trims are now written as absolute PulseAudio native-volume values. This preserves independent dB targets without mixing pactl's relative negative-dB syntax with absolute channel values, and verifies the exact dB readback after restoration.

## 3.3.20 Safe Headroom state loading

Saved EQ curves now survive the normal state-loading path, so startup Safe Headroom calculates its target from the restored curve before applying and verifying live `preamp:Mult`.

## 3.3.19 verified Safe Headroom startup

GUI and login startup now repeatedly apply and read back the calculated `preamp:Mult` through a bounded settling window. The UI reports the actual live attenuation if verification fails.

## 3.3.18 Ubuntu speaker-test numbering

Ubuntu Pulse speaker tests now use the hardware-verified ALSA selection order: FL=1, FC=2, FR=3, RR=4, RL=5, and LFE=6. Bazzite behavior is unchanged.

## 3.3.17 Ubuntu regression correction

- Restores Ubuntu Speaker Fill and Pulse speaker testing to the verified v3.3.2 paths.
- Retains Bazzite's v3.3.15 persistent stereo-fill sink and hardware-verified PipeWire speaker mapping.
- Restores channel calibration with explicit dB values and verifies both channel trims and Safe Headroom after startup.

## 3.3.14 stereo-only Speaker Fill

Speaker Fill now applies only to true two-channel playback; native multichannel audio remains discrete. The verified 3.3.12 Bazzite speaker-test correction is retained.

## 3.3.12 speaker-test channel correction

- Uses `soundblaster_zse_eq` as the authoritative default sink whenever the EQ is healthy.
- Moves already-running playback streams to the EQ route when activated.
- Keeps the physical AC3 5.1 sink as fallback only.
- Speaker and bass test tones explicitly target the EQ sink and preserve the system route.


## 3.3.10 Bazzite stability correction

- Removes automatic 30-second EQ recovery from the connection-status poller.
- A missing EQ can no longer restart the desktop PipeWire/WirePlumber stack.
- When the physical AC3 5.1 sink is healthy, the UI explicitly reports `EQ unavailable • AC3 5.1 fallback active`.
- Adds a user-driven **Retry EQ** action. On Bazzite it restarts only `filter-chain.service`; it never restarts PipeWire, PipeWire-Pulse, or WirePlumber.
- Preserves v3.3.3 channel restore/readback logic and all later Bazzite AC3/dependency fixes.

A Linux/PipeWire control panel for Sound Blaster-class audio devices and common stereo through 5.1 speaker layouts. The installer detects the user's physical PipeWire output sink at install/runtime rather than embedding a machine-specific PCI address, ALSA card number, username, or hostname.

## What 2.0 adds

- True live 10-band EQ using PipeWire `bq_peaking` filters and `pw-cli` (no PipeWire restart for ordinary EQ slider movement).
- Built-in **Flat, Gaming, Music, Movies, and Night** presets plus five named custom preset slots.
- **Master processing bypass** for quick A/B comparison.
- **Independent FL, FR, FC, LFE, RL, and RR trims**, plus master preamp.
- **Safe Headroom** applies a non-destructive effective DSP gain ceiling when boosted EQ settings need extra headroom; it never rewrites your Master Preamp slider.
- Live headroom warning and one-click Auto Headroom.
- Auto-save of current controls and startup restore of the last state.
- Duplicate-window prevention: launching the app again raises the existing window instead of creating another controller.
- PipeWire path status, automatic reconnect, and manual Reconnect button.
- Device Setup tab to select the physical sink that `soundblaster_zse_eq` feeds.
- Speaker-fill controls, rear delay, stereo width, LFE crossover, mute, and six-channel speaker test.
- Desktop launcher and login restore entry.
- Upgrade migration from the earlier `~/.config/soundblaster-zse-control.json` state format.

## Requirements

- Linux with PipeWire, pipewire-pulse, and WirePlumber.
- Python 3 with Tk (`python3-tk` on Ubuntu).
- `pactl`, `pw-cli`, and `pw-dump`.
- `speaker-test` / `alsa-utils` is optional but required for the built-in speaker test buttons.
- A physical output capable of receiving the six-channel stream. For an optical AC3/Dolby Digital Live setup, this will commonly be a sink whose name contains `iec958-ac3-surround-51`.

Ubuntu example:

```bash
sudo apt install python3-tk pipewire pipewire-pulse wireplumber pipewire-bin pulseaudio-utils alsa-utils
```

## Install / upgrade

Extract the archive and run:

```bash
./install.sh
```

The installer will:

1. Back up existing `soundblaster_zse_eq`, speaker-fill, desktop-launcher, and autostart files.
2. Migrate the old saved state if present.
3. Preserve the current physical target from an existing `soundblaster-zse-eq.conf`, or detect a likely 5.1/AC3 sink.
4. Preserve the current 10-band gains while upgrading the filter graph.
5. Install the application under `~/.local/lib/soundblaster-zse-control/` with a launcher in `~/.local/bin/`.
6. Restart the user's PipeWire stack once and set `soundblaster_zse_eq` as the default sink.

To explicitly choose a hardware sink:

```bash
pactl list short sinks
./install.sh --sink 'alsa_output.example.iec958-ac3-surround-51'
```

To install files without restarting audio immediately:

```bash
./install.sh --no-restart
```

## Run

From the desktop application menu, open **Sound Blaster Linux Control Center**, or run:

```bash
soundblaster-zse-control
```

Diagnostics:

```bash
soundblaster-zse-control --check
soundblaster-zse-control --version
```

The login restore command is:

```bash
soundblaster-zse-control --restore
```

## Presets and headroom

Built-in presets alter EQ and channel levels but deliberately leave the user's speaker-fill/spatial configuration alone. Custom presets capture the full current control state.

Safe Headroom is a conservative guard, not a true digital peak meter. It estimates the gain ceiling needed for positive EQ boost and applies that ceiling to the **effective DSP preamp** without changing the Master Preamp slider. Turning Safe Headroom off immediately restores the requested preamp. Positive channel trims remain user-controlled and are included in the clipping-risk display.

## Master bypass

Master bypass temporarily sets the live EQ gains and per-channel/preamp processing to unity without overwriting the saved slider values. Turning bypass off reapplies the current controls.

## Files

- App: `~/.local/lib/soundblaster-zse-control/control.py`
- Command: `~/.local/bin/soundblaster-zse-control`
- State/presets: `~/.config/soundblaster-zse-control/state.json`
- Live EQ graph: `~/.config/pipewire/filter-chain.conf.d/soundblaster-zse-eq.conf`
- Speaker fill: `~/.config/pipewire/pipewire-pulse.conf.d/10-speaker-fill.conf`
- Desktop launcher: `~/.local/share/applications/soundblaster-zse-control.desktop`
- Startup restore: `~/.config/autostart/soundblaster-zse-restore.desktop`

## Uninstall

```bash
./uninstall.sh
```

The uninstaller intentionally leaves the EQ config and presets in place so an uninstall does not unexpectedly destroy the user's audio configuration. The script prints those paths if a complete manual removal is desired.

## Notes for other hardware

This package keeps the virtual sink name `soundblaster_zse_eq` for compatibility, but the physical target is configurable. The six-channel position is fixed to:

`FL FR FC LFE RL RR`

Hardware/driver combinations that expose a different channel map or only stereo may require a separate profile. The Device Setup tab is intended to make target-sink changes safe without hand-editing the PipeWire filter file.


## Smart-filter routing

In KDE/system audio settings, applications should target the real Sound Blaster 5.1 IEC958/AC3 sink. WirePlumber inserts the Sound Blaster Linux EQ automatically. The Control Center Device Setup page selects which physical sink the smart filter follows.

## Preset indicators and spectrum analyzer

The main **EQ & Levels** page now contains one-click buttons for both built-in and custom presets. The recalled preset is highlighted; changing an EQ, preamp, or channel slider changes the status to **Modified** so the indicator remains truthful. Custom preset **Save / Rename** management remains on the **Presets & Test** page.

A lightweight spectrum analyzer is displayed beside the EQ. Live Output Levels are captured from the final physical Sound Blaster sink by creating an unconnected `pw-record` stream and explicitly linking each physical `monitor_*` port to the matching recorder input with `pw-link`. This avoids Pulse remixing and PipeWire target-port guessing, so the six meters represent the actual digital channels headed toward the hardware. The analyzer is visualization-only and does not modify the audio path. If `pw-record`/`pw-link` are unavailable, audio processing continues normally and the analyzer reports that PipeWire tools are required.


### Preset behavior
EQ presets store and recall only the 10-band EQ curve. Master Preamp and per-channel trims are persistent global/speaker-calibration controls and do not change when presets are selected.

## 3.2.0 Line Input controls
The Line Input tab can select the physical Sound Blaster input port and provides persistent Input Level and Mic Boost controls. Mic Boost is implemented as PipeWire/Pulse software capture gain for portability across cards and Linux distributions.


## 3.2.1 Microphone processing

The Line Input tab can create an optional **Sound Blaster Processed Mic** source with three-band voice EQ and adjustable PipeWire noise-gate reduction. Enable it, choose the physical microphone input, click **Apply / Rebuild Mic Source**, then select **Sound Blaster Processed Mic** in the voice/recording application. The physical source remains available.


## 3.3.0 distribution support

The installer detects Debian/Ubuntu-family, Fedora, Arch-family, and Bazzite/Fedora Atomic systems. It installs only missing dependencies on mutable distributions. On Bazzite/Atomic it does not automatically layer packages; if a required host audio component is missing it prints the required rpm-ostree command and exits so the user can make that system-level change explicitly.


## Privacy / portability audit

The distributable package contains no developer username, home directory, hostname, fixed PCI address, fixed ALSA card number, Arctis/SteelSeries device identifier, or session-specific PipeWire numeric node ID. Runtime device names and paths are detected on the installed system. Legacy `z5500` filenames are referenced only for migration/removal of older releases.

Project signature/contact: **!!ZuEs!!** — `zuestgg@gmail.com`

## Quick start

For most users:

```bash
tar -xzf soundblaster-linux-control-center-3.3.39.tar.gz
cd soundblaster-linux-control-center-3.3.39
./install.sh
```

The installer checks the host distribution, installs missing dependencies on supported mutable distributions, detects a suitable physical output, installs the app into the current user's home directory, and restarts the user PipeWire audio stack once. No root account is needed for the app itself; `sudo` is used only if the installer needs to install missing system packages.

After installation, launch **Sound Blaster Linux Control Center** from the application menu or run:

```bash
soundblaster-zse-control
```

For optical 5.1, the physical Sound Blaster output must expose a 5.1 AC3/A52-capable sink. To see available outputs:

```bash
pactl list short sinks
```

If automatic detection chooses the wrong output, reinstall/select it explicitly:

```bash
./install.sh --sink 'FULL_PIPEWIRE_SINK_NAME'
```

See **TROUBLESHOOTING.md** for common audio, 5.1, microphone, analyzer, and installation problems.


### Analog multichannel status (v3.3.68-test1)
Analog 2.0/2.1 is the conservative baseline. Analog 4.0, 4.1, 5.0 and 5.1 are **EXPERIMENTAL** and may not produce independent outputs on every CA0132 card or Linux kernel/driver. Digital AC3 5.1 is a separate, verified path on supported hardware.

### Audio-device selection
Linux/PipeWire/WirePlumber should choose active audio devices. SBLCC does not have headset-brand dependencies. The optional **Use Sound Blaster** button deliberately makes the SBLCC virtual EQ default and moves currently playing streams once; it does not prevent later user/device-driven selection.

### Background audio return (v3.3.68-test4)

An optional user-level systemd observer monitors changes to the system default
output. It does **not** select Sound Blaster over a headset. Only after the
system selects the configured Sound Blaster does it attempt to recover the
saved surround profile and EQ without the GUI open. It is independent of headset
brands and uses standard PipeWire/pactl APIs. The systemd user service is
`soundblaster-zse-audio-return.service`. If desired, disable with
`systemctl --user disable --now soundblaster-zse-audio-return.service`.

This is experimental and has not yet been verified on all distros.
