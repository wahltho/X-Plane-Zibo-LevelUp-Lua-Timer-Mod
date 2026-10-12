# Independent Lua Timer Mod

This is an experimental, optional patch for Zibo and LevelUp. It is developed
and supported by wahltho, independently of both aircraft teams. RandomUser
(JT8D-17) agreed to adapting his Timer Mod; his work prompted this project.
Original project: https://github.com/JT8D-17/Zibo-737-Lua-Timer-Mod

Repository: https://github.com/wahltho/X-Plane-Zibo-LevelUp-Lua-Timer-Mod

The original mod runs whole scripts at 20 Hz. That changes frame-based timers
and the order of some callbacks. This version keeps all physics callbacks at
their original frame rate and phase. `SIM_PERIOD`, replay handling, W&B and
the Tablet callbacks are unchanged.

Currently, only two pure FMS geometry functions are optimized: great-circle
distance and bearing. Identical numeric inputs can reuse a result for less
than 50 ms of simulator time. A changed input is calculated immediately. The
cache is bounded to one entry per function, uses no scheduled callbacks and
does not quantize coordinates. After 16 consecutive cache misses it restores
the original function, so continuously changing coordinates do not keep
paying cache overhead. Unknown helper implementations are rejected.

This is deliberately narrower than the original Timer Mod. An isolated
benchmark is not a simulator FPS result. Flight and performance validation
in X-Plane remains open. The first release is **0.1.0-beta.1**; it is intended
for testing, without a promised FPS improvement.

Latest release: https://github.com/wahltho/X-Plane-Zibo-LevelUp-Lua-Timer-Mod/releases/latest

## Installation

Close X-Plane first. Extract the complete package outside the aircraft folder.
Use Python 3:

```text
python3 z_Install.py install --aircraft-root "/path/to/aircraft"
python3 z_Install.py update --aircraft-root "/path/to/aircraft"
python3 z_Install.py uninstall --aircraft-root "/path/to/aircraft"
```

On Windows, replace `python3` with `py -3`. Restart X-Plane afterwards.
The installer preserves line endings, UTF-8 BOM, file permissions and unrelated
edits. Its private receipt and original backups are kept under
`.patch-ownership/wahltho.zibo-levelup-737ng.lua-timer/`. Do not delete these.

MTK is the recommended installation path when you use other MTK patches.
Use MTK 0.28.2 or newer, select your aircraft and review its patch group.
Select **Lua Timer Mod (Beta)** under the optional patches, then apply your
selection. It is available for Zibo and LevelUp and is not selected by default.
Restart MTK if it was open while the new catalog was published.

The same release ZIP contains the standalone installer and the schema-3 MTK
source package. The `catalog/` files are integration templates, not a second
installer. Beta appears in the version and display name. The GitHub release
uses the regular release feed so existing MTK clients can discover it.

Use one manager for files shared with other patches. The standalone installer
blocks an overlapping MTK installation; MTK blocks an unowned or standalone
Timer installation. Uninstall through the current owner before switching.
Matching hashes do not authorize adoption. Legacy `timed_before_physics` or
`timed_after_physics` edits must be removed using verified original backups;
this installer does not guess which `.bak` is safe.

## Development

`python3 tools/build_package.py --version 0.1.0-beta.1` regenerates the local
manifest and inventory. `python3 tools/build_release.py` builds the release
ZIP and checksums from an explicit file list.
Updates must explicitly list previously supported helper hashes. Do not upload
test-only versions used by the lifecycle tests.

Tests use disposable copies and the released MTK Core. See
`tests/README.md` for the commands and the recorded boundaries of the proof.
GitHub Actions checks package integrity and the Lua runtime suite on every
push. Full aircraft, native XLua and MTK lifecycle tests require local inputs;
these inputs and their backups are excluded from Git.

## License and credits

Original code in this project uses the MIT license. The native XLua test
sources retain their own MIT notice under `tests/native`. Aircraft source
files are not redistributed. Short source anchors identify the exact functions
that a patch can safely modify; they do not grant rights to the aircraft code.
See `THIRD_PARTY.md` for source attribution and test prerequisites.

Support for this independent project: https://discord.gg/ySS88PMuyC
Do not ask the official Zibo or LevelUp support teams to debug this patch.
