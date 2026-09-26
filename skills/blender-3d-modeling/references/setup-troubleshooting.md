# Blender MCP Setup Troubleshooting (L1–L6)

Run the layer probe first (from the managed Blender plugin root, or absolute):

```bash
python3 <plugin>/scripts/blender_health.py --json            # all layers
python3 <plugin>/scripts/blender_health.py --skip-mcp --json # env only, fast
```

Layers: **L1** Blender ≥ 5.1 · **L2** uv/uvx · **L3** durable server env warmed · **L4** official
addon installed · **L5** Blender running + port 9876 listening · **L6** end-to-end MCP handshake.

## Failure → root cause → fix (all hit in real sessions)

### L1 fail: "Blender version below 5.1"
Official addon requires Blender ≥ 5.1. Guide the user to install Blender 5.2 LTS from
blender.org and replace /Applications/Blender.app. Do not attempt workarounds on 4.x.

### L2/L3 fail: uvx "Git operation failed" / `git init` exit 72 with Xcode loader errors
The system `/usr/bin/git` is a broken Xcode shim (`libxcodebuildLoader.dylib` symbol errors).
Do NOT retry as-is. If a Homebrew git exists, warm with it first in PATH:

```bash
/opt/homebrew/bin/git --version   # sanity check
PATH="/opt/homebrew/bin:$PATH" python3 <plugin>/scripts/blender_setup.py warm
```

### L4 fail: addon not installed
Requires Blender **fully closed** — installing while it runs gets overwritten on quit. Check with
`pgrep -x Blender` (exact match; `pgrep -f Blender.app` also matches your own shell command
string and lies). Then:

```bash
python3 <plugin>/scripts/blender_setup.py install-addon --yes
```

### L5 fail: Blender running but port 9876 closed — four root causes, in check order

1. **This GUI instance predates the addon install.** Preferences load at launch; an instance
   started before `install-addon` never sees the addon. Fix: restart Blender.
2. **`bpy.app.online_access` is off** — the addon refuses to autostart without it (its
   `startup_online_ok_or_error` gate). Launch with online mode:
   `open -a Blender --args --online-mode`. For permanent use, the user ticks Preferences →
   System → Network → "Online Access" once.
3. **Addon disabled**: query on-disk prefs with a background instance (only while GUI is closed,
   otherwise the GUI overwrites prefs on quit with stale data):
   ```bash
   "/Applications/Blender.app/Contents/MacOS/Blender" -b --python-expr "
   import bpy
   a = bpy.context.preferences.addons.get('bl_ext.user_default.mcp')
   print('ENABLED:', bool(a), '| autostart:', getattr(a.preferences,'use_autostart',None) if a else None)"
   ```
4. **First-launch delay**: autostart fires after `autostart_delay` seconds; give a fresh launch
   ~20–30 s before declaring failure.

### Graceful restart of the GUI
```bash
osascript -e 'tell application "Blender" to quit'
```
`User canceled (-128)` may still be followed by a clean exit — always confirm with `pgrep -x
Blender` instead of trusting the AppleScript result. Never force-kill a user's Blender; it may
hold unsaved work.

### L6 fail: "Cannot connect to Blender at localhost:9876"
The stdio server is fine but no in-Blender server is listening — treat as L5. If the GUI was up
and vanishes between calls, the user quit it; ask them to reopen (with `--online-mode` args if
cause 2 applies).
