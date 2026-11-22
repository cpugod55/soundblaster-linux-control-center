# Sound Blaster Linux Control Center v3.3.7 — Community Testing Pre-release

This release is the hardware-tested **v3.3.68-test4** development build renamed **v3.3.7** for wider testing. This tag is intentionally named as requested, although GitHub version sorting may place it before v3.3.39. Audio logic is unchanged from test4.

## Highlights

- PipeWire/WirePlumber-compatible Sound Blaster control with digital AC3 5.1, EQ, safe headroom, individual channel trims, and optional stereo Speaker Fill.
- GUI-independent user audio-return helper: after the OS switches from a headset back to Sound Blaster, restore the saved DSP/configuration while leaving unrelated output devices alone.
- Manual **Use Sound Blaster** selection button (not a permanent force-default mode).
- Analog modes above 2.1 explicitly marked **EXPERIMENTAL**; hardware/driver channel routing varies.

## What has actually been tested

- Maintainer: Ubuntu 26.04 KDE, Creative Sound Blaster Z-series CA0132, digital AC3 5.1 to Logitech Z-5500.
- Switching to headset, closing the GUI, and switching back restored AC3 5.1 plus EQ and Speaker Fill after about **1–2 seconds**.
- Static/simulation tests are not a substitute for hardware tests; other distributions remain unverified for this build.

## Requirements and installation

A Linux desktop with PipeWire/WirePlumber and the application's supported dependencies, including Python 3/Tk, ALSA tools, pactl, and a **systemd user session** for the optional return observer. The user-local installer detects some supported distributions and may request sudo for missing OS packages; it does not require launching the installer itself as root.

```bash
# after downloading/extracting the matching tarball
cd soundblaster-linux-control-center-3.3.7
./verify_package.sh
./install.sh
systemctl --user status soundblaster-zse-audio-return.service --no-pager
```

If the background helper misbehaves:

```bash
systemctl --user disable --now soundblaster-zse-audio-return.service
```

Keep a known-working earlier package for rollback. See README, UPGRADE_NOTES, TROUBLESHOOTING, and uninstall.sh.

## Please report

Distribution and version, desktop session (Wayland/X11), PipeWire and WirePlumber versions, Creative USB/PCI identifiers, output type (digital/analog), observed channel layout and specific reproduction steps. Remove private identifiers from logs before sharing them.
