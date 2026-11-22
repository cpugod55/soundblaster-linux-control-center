# v3.3.68-test4 targeted fix

User restore.log from v3.3.68-test3 showed `device-return: unexpected failure: name 'update_fill_processing' is not defined` even though EQ and headroom restored.

Root cause: `--restore-selected` executes before the module has reached definitions of `update_fill_processing`, `playback_sink_inputs`, `_sink_id_name_map`, and `_fill_output_id` which were located in the GUI setup section. Those definitions are now hoisted above the CLI dispatch.

Test: headset on → GUI closed → headset off; verify actual surround output. Keep GUI closed to collect `restore.log` if failure continues. This build has not been validated against live audio hardware.

# v3.3.68-test4 — closed-GUI routing recovery (experimental)

Based on v3.3.68-test2; v3.3.65 Fix2 is the stable rollback.

- Background observer now notices sink-input-to-sink routing changes even if `pactl get-default-sink` does not change.
- On Sound Blaster selection only, headless recovery now reasserts bass DSP and existing Speaker Fill controls.
- Only stereo streams ALREADY on the SBLCC EQ are moved to SBLCC Fill; never pulls audio away from another device. No forced default switching, no global PipeWire restart, no guessed analog profile.
- Per-user systemd service still uses distro-neutral `pactl` / PipeWire tools. Real cross-distribution verification is still required.

## Ubuntu KDE test
1. With GUI open verify optical AC3 5.1, EQ, Speaker Fill.
2. Turn headset on; confirm device takeover works. Close GUI.
3. Turn headset off; confirm returns to digital 5.1 with EQ and fill restored.
4. Test *Use Sound Blaster* button manually.
5. Check that selecting other output never causes SBLCC to steal audio.

## Service logs
`systemctl --user status soundblaster-zse-audio-return.service --no-pager`
`tail -50 ~/.config/soundblaster-zse-control/restore.log`

## Immediate rollback
`systemctl --user disable --now soundblaster-zse-audio-return.service`

Restore from the saved v3.3.65 Fix2 installer if needed.
