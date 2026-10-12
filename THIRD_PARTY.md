# Sources and credits

RandomUser (JT8D-17)'s Timer Mod prompted this project. He gave Thomas
permission to develop an MTK-compatible variant. This implementation takes
a different approach: it caches two pure calculations and keeps the original
physics callbacks. The original installer is not included.

Original repository: https://github.com/JT8D-17/Zibo-737-Lua-Timer-Mod
Reviewed revision: `0acab2c978be6e1b6d96de27eb64e2f1ec9351f7`.

The structural patch descriptions contain short source anchors from the
Zibo/LevelUp FMS script. Those anchors identify supported function bodies.
Their inclusion does not transfer ownership of the aircraft code. Complete
aircraft scripts, aircraft archives and test aircraft are not included.

The callback harness under `tests/native` uses MIT-licensed XLua source.
Its source versions and the boundaries replaced by test stubs are recorded
in `tests/native/PROVENANCE.md`; the copyright notice is retained in
`tests/native/LICENSE.txt`.

The X-Plane SDK, LuaJIT static library, released MTK Core DLL and aircraft
fixtures needed by local integration tests must be supplied separately.
No compiled third-party runtime is stored in this repository.
