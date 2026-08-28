## EQ unavailable on Bazzite (3.3.10+)

If the app shows **EQ unavailable • AC3 5.1 fallback active**, audio remains routed through the physical six-channel AC3 sink. Use **Retry EQ** once after checking the filter-chain service. The app will not restart PipeWire, PipeWire-Pulse, or WirePlumber automatically.

# Sound Blaster Linux Control Center — Troubleshooting

These checks are safe starting points. The application uses PipeWire/WirePlumber and detects device names at runtime; do not copy numeric sink/source IDs from another computer because those IDs change between machines and sessions.

## 1. Basic diagnostics

Run:

```bash
soundblaster-zse-control --check
pactl info | grep 'Default Sink'
pactl list short sinks
pactl list short sources
wpctl status
```

`--check` reports the installed Control Center version, whether its EQ/fill configuration exists, the configured hardware target, whether the virtual EQ sink exists, and the current default sink.

If the app is open but audio routing looks wrong, first use **Device Setup → Reconnect Now**.

## 2. No sound after installation

Check that the physical output still appears in:

```bash
pactl list short sinks
```

Then open **Device Setup** in the Control Center, select the intended physical output and apply/reconnect it. For an optical 5.1 setup, choose the Sound Blaster sink that identifies itself as surround 5.1 / AC3 when available.

If PipeWire needs a clean restart:

```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

Then reopen the Control Center.

## 3. Only stereo / 5.1 optical output is missing

The application cannot invent a hardware/driver profile that Linux does not expose. First inspect:

```bash
pactl list short sinks
pactl list cards
```

For the optical Dolby Digital/AC3 path, the desired sink commonly contains `iec958-ac3-surround-51`, `surround-51`, or `ac3` in its name. If the installer found the wrong sink, rerun it with:

```bash
./install.sh --sink 'FULL_PIPEWIRE_SINK_NAME'
```

The installer can attempt the required A52/AC3 host support on supported mutable distributions. `./install.sh --no-optical-setup` disables that attempt.

## 4. Other headphones or speakers disappeared

The Control Center should not remove unrelated devices. Check **Devices**, **Sinks**, and **Sources** separately:

```bash
wpctl status
```

A device can still be detected while its playback sink is absent because its profile is disabled or changed. Do not hard-code a numeric ID into the Control Center; select devices by their current names/profile through the system or Device Setup.

## 5. Spectrum analyzer does not move

The analyzer uses `parec` to listen to the processed sink monitor. Audio processing itself still works if the analyzer is unavailable.

Check:

```bash
command -v parec
```

On Debian/Ubuntu-family systems it is normally supplied by `pulseaudio-utils`. On Fedora-family systems the installer also checks the package providing the PulseAudio compatibility utilities. Restart the app after installing the missing utility.

## 6. Speaker Test does not work

The test buttons require `speaker-test` from `alsa-utils`:

```bash
command -v speaker-test
```

If the command is missing, install the distribution's `alsa-utils` package and reopen the app.

## 7. Microphone or Line In is missing

Inspect the physical capture sources:

```bash
pactl list short sources
```

If the Sound Blaster exposes Microphone and Line In as ports on one source, the Control Center switches the port rather than creating two physical source entries. Choose the physical source and the desired port on the **Line Input** tab.

Input Level and Mic Boost affect capture gain. If a hardware-specific boost control is not exposed portably, Mic Boost uses software capture gain.

## 8. Processed microphone is missing

On **Line Input**, enable **Processed Mic**, choose the physical microphone, and click **Apply / Rebuild Mic Source**. The new source should appear as:

`Sound Blaster Processed Mic`

Check it with:

```bash
pactl list short sources
```

Then select **Sound Blaster Processed Mic** inside Discord, Steam, recording software, or the system input selector. The original physical microphone remains available.

## 9. Line Input monitoring will not start

Line monitoring uses `pw-loopback`. Check:

```bash
command -v pw-loopback
```

Also make sure a valid input source/port and hardware output are selected. Monitoring is session-only and stops when the Control Center/session closes.

## 10. EQ sliders move but the sound does not change

Use **Device Setup → Reconnect Now**, then run:

```bash
soundblaster-zse-control --check
wpctl status
```

Confirm `soundblaster_zse_eq` exists and the configured target is the intended physical Sound Blaster sink. Master Bypass intentionally disables the processing for A/B comparison, so make sure it is not enabled while testing EQ changes.

## 11. Wrong output became the system default

List sinks:

```bash
pactl list short sinks
```

You can temporarily choose a physical output with the desktop sound settings. The Control Center's Device Setup page controls which physical sink its processing path follows.

## 12. Installation dependency problems

Supported installer families are Debian/Ubuntu/Mint/Pop!_OS, Fedora, Arch/Manjaro/EndeavourOS, and Bazzite/Fedora Atomic.

Bazzite/Atomic is intentionally conservative: the installer does **not** automatically layer missing host packages. If a required host component is missing, it prints the `rpm-ostree install ...` command and exits so the user can decide whether to layer it.

On an unrecognized distribution, install these equivalents manually before rerunning the installer:

- Python 3 and Tk/Tkinter
- PipeWire and PipeWire Pulse compatibility
- WirePlumber
- `pactl`
- `pw-cli`, `pw-dump`, and `pw-loopback`
- ALSA utilities (`speaker-test`)

## 13. Collecting useful information for a bug report

Please include the output of:

```bash
soundblaster-zse-control --version
soundblaster-zse-control --check
wpctl status
pactl list short sinks
pactl list short sources
```

Also state the Linux distribution/version, desktop environment, Sound Blaster model, connection type (analog or optical), and what you expected versus what happened. Avoid posting unrelated private system information.

Contact: **!!ZuEs!! — GitHub Issues**

## Bazzite: JamesDSP or stale `jamesdsp_sink` routing

JamesDSP is not required by Sound Blaster Linux Control Center. A previous JamesDSP installation can leave WirePlumber stream-restore entries targeting `jamesdsp_sink`. This can misroute speaker tests or interfere with Spatial and Speaker Fill even when the Sound Blaster graph itself is correct.

If JamesDSP was installed only for Sound Blaster troubleshooting, remove it, restart the user `wireplumber`, `pipewire`, and `pipewire-pulse` services, then reopen the control center. If routing remains wrong, inspect `~/.local/state/wireplumber/stream-properties` for Sound Blaster or `speaker-test` entries that still contain a `jamesdsp_sink` target. Back up that file before editing stale entries.
