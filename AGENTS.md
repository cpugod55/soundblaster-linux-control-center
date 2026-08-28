# Repository Guidelines

## Project Structure & Module Organization

The application is a compact Python/Tkinter desktop tool. Its main implementation lives in `app/soundblaster_zse_control.py`; keep UI, PipeWire integration, state migration, and preset behavior coherent when changing this file. Static artwork belongs in `assets/`. Distribution and lifecycle logic is in `install.sh`, `uninstall.sh`, and `verify_package.sh`. User-facing behavior and release history are documented in `README.md`, `TROUBLESHOOTING.md`, `UPGRADE_NOTES.md`, and `CHANGELOG.md`.

Do not commit generated files such as `app/__pycache__/` or machine-specific PipeWire names, home paths, node IDs, and device identifiers.

## Build, Test, and Development Commands

- `./verify_package.sh` compiles the Python source, validates shell syntax, and checks required package documents. Run it before every submission.
- `python3 app/soundblaster_zse_control.py --check` performs application diagnostics against the local audio environment.
- `python3 app/soundblaster_zse_control.py --version` verifies version metadata without opening the GUI.
- `./install.sh --no-restart` installs locally while avoiding an immediate audio-stack restart. Use `./install.sh --sink 'PIPEWIRE_SINK_NAME'` only when testing explicit routing.
- `./uninstall.sh` removes installed application files while preserving user EQ configuration and presets.

There is no separate build system or automated unit-test suite; package verification is the required baseline.

## Coding Style & Naming Conventions

Use four-space indentation and standard Python conventions: `snake_case` for functions and variables, `UPPER_CASE` for constants, and short docstrings where behavior is not obvious. Keep subprocess calls argument-based (for example, `run(["pactl", ...])`) rather than shell-interpolated. Shell scripts use Bash, `set -euo pipefail`, uppercase environment/configuration variables, quoted expansions, and two-space indentation inside blocks. Preserve the canonical six-channel order: `FL FR FC LFE RL RR`.

## Testing Guidelines

Add focused checks to `verify_package.sh` when introducing package-level invariants. For audio or UI changes, manually test startup, `--check`, state save/restore, reconnect behavior, and the affected stereo/5.1 route. Avoid tests that silently restart PipeWire or overwrite a developer's live configuration.

## Commit & Pull Request Guidelines

Git history is not available in this source snapshot. Use concise, imperative commit subjects such as `Fix EQ sink recovery on Bazzite`, and keep unrelated changes separate. Pull requests should describe user-visible behavior, supported distribution/audio path, manual verification performed, and configuration migration impact. Link relevant issues and include screenshots for UI changes. Update `CHANGELOG.md` and version references together for releases.
