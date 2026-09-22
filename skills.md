---
name: openmausbot-config
description: Change OpenMausBot settings safely and discover which knobs exist — config.json keys (rooms.turnTimeoutMinutes, handoff limits, vps, browserEngine), OMB_* env vars, and the quit/backup/edit/relaunch procedure. Use whenever the user wants to change an OpenMausBot setting or timeout, edit ~/.openmausbot/config.json, asks whether something is configurable, or hits a limit/watchdog they want to tune.
---

# Configuring OpenMausBot

Two jobs when this skill triggers:

1. **Change a setting safely** — the golden procedure below, every time.
2. **Answer "is X configurable?"** from evidence — grep the app bundle; never
   guess key names. Read [references/keys.md](references/keys.md) for every
   knob verified against the installed version.

## The golden rule

`~/.openmausbot/config.json` is read **only at startup**, and the running app
holds its own in-memory copy that it can write back over the file at any
time. Editing under a live app means the edit can silently vanish. So:

1. **Quit the app gracefully** — never `kill -9` (state is worth saving):
   ```bash
   osascript -e 'tell application "OpenMausBot" to quit'
   for i in $(seq 1 20); do pgrep -f "OpenMausBot.app/Contents/MacOS/OpenMausBot" >/dev/null || break; sleep 1; done
   ```
2. **Back up** the config with a dated suffix:
   ```bash
   cp ~/.openmausbot/config.json ~/.openmausbot/config.json.bak-$(date +%Y%m%d)
   ```
3. **Edit with a JSON-aware tool, merging** so sibling keys survive:
   ```python
   cfg = json.load(open(p))
   cfg['rooms'] = {**(cfg.get('rooms') or {}), 'turnTimeoutMinutes': 20}
   json.dump(cfg, open(p, 'w'), indent=2)
   ```
4. **Relaunch and verify**:
   ```bash
   open -a OpenMausBot && sleep 3 && pgrep -f OpenMausBot.app/Contents/MacOS
   ```
5. Confirm the change took effect in behavior (or the log), because an
   invalid value can make the schema reject just that key.

Viewing the file in an editor while the app runs is fine; only *saving* edits
under a live app risks being overwritten.

## How to discover whether something is configurable

The truth is one minified file:
`/Applications/OpenMausBot.app/Contents/Resources/server/index.js`.
Grep it — do not trust remembered line numbers or key names across app
versions (check the version first with `defaults read
/Applications/OpenMausBot.app/Contents/Info.plist CFBundleShortVersionString`).

- **Config keys** surface as accessors: `cfg?.rooms?.turnTimeoutMinutes ?? DEFAULT_...`
  — any `cfg.<section>.<key> ?? DEFAULT` is a config.json key.
- **Defaults and bounds** live next to them: `var DEFAULT_ROOM_TURN_TIMEOUT_MINUTES = 5`,
  and schema lines like `.number().int().min(1).max(1440)` give valid ranges.
  Cross-field rules appear as `.refine(...)` (e.g. rooms handoff ordering).
- **Documented keys in error strings**: grep `to ~/.openmausbot/config.json`
  — the code explains its own keys (`add {"box":{"token":"…"}} to ~/.openmausbot/config.json`).
- **Env vars**: `grep -o "process\.env\.OMB_[A-Z_]*" index.js | sort -u`.
  Mind the **second prefix**: some vars are `OPENMAUS_*` (e.g.
  `OPENMAUS_ACP_PROMPT_IDLE_TIMEOUT_MS`). Env vars for a GUI-launched app
  need `launchctl setenv VAR value` followed by an app restart (does not
  persist across reboots).
- **The watchers are distinct** — check which one fired before tuning:
  "room turn exceeded N minutes" → `rooms.turnTimeoutMinutes`;
  "went fully silent Ns" → `OPENMAUS_ACP_PROMPT_IDLE_TIMEOUT_MS`;
  routine stopped for no activity → routine settings; "Same call repeated
  N×" → not configurable at all (see below).

## Known NOT configurable

The tool-loop warning ("Same call repeated 5×/10×/20× — … — it may be
stuck") comes from `new RepeatDetector({ thresholds: [5, 10, 20] })` with
literal values — no config key, no env var. It is a warning only; it never
stops a turn. Don't hunt for a setting; fix the loop instead (see the
sibling skill `local-llm-tool-calling` for diagnosing the model behavior
that causes repeats, and for reading `~/Library/Logs/openmausbot/server.log`
and the `~/.openmausbot/messages.db` SQLite history).

## Version drift

Every key, default, and line reference in [references/keys.md](references/keys.md)
was verified against a specific app version (named at the top of that file).
After an app update, re-run the greps above before trusting the reference —
the updater replaces the bundle wholesale.
