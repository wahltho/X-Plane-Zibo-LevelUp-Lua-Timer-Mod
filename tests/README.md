# Tests

These tests use disposable aircraft copies. They do not change an X-Plane
installation, the live catalog or another patch repository.

## Checks that need no aircraft installation

Python 3 and LuaJIT 2.1 are sufficient for the checks run by GitHub Actions:

```sh
python3 -m compileall -q z_Install.py standalone_guard.py tools tests/test_installer.py
python3 -c 'from pathlib import Path; from standalone_guard import verify_text_manifest; from z_Install import PACKAGE_ID; print(verify_text_manifest(Path.cwd(), PACKAGE_ID))'
python3 tools/prepare_runtime_tests.py
TIMER_PROJECT_ROOT="$PWD" luajit tests/runtime.lua
```

These checks verify the source package and the Lua helper/loader behaviour.
They do not substitute for the aircraft, XLua callback or MTK lifecycle tests.

## Local integration tests

Supply local inputs through the following environment variables. The tools
fail with an explicit message if a required input is missing; they do not
silently skip the integration matrix.

| Variable | Input |
| --- | --- |
| `TIMER_PROJECT_ROOT` | Absolute path to this checkout |
| `TIMER_MTK_CHECKOUT` | MTK checkout with the current catalog |
| `TIMER_PACKAGE_EVIDENCE` | Verified group cache; `inputs/zibo-737ng-group-path.txt` and `inputs/levelup-737ng-group-path.txt` contain absolute paths to provisioned groups |
| `TIMER_ZIBO_AIRCRAFT` | Zibo 4.05.35 fixture, with aircraft files and original Lua scripts |
| `TIMER_LEVELUP_AIRCRAFT` | LevelUp fixture, with aircraft files and objects matching its group manifest |
| `TIMER_LEVELUP_SCRIPTS` | Original LevelUp fixture root containing `plugins/xlua/scripts` |
| `TIMER_XLUA_CHECKOUT` | XLua source directory with `lua_sdk/libluajit_mac.a` and `SDK/CHeaders/XPLM` |
| `TIMER_MTK_CORE_DLL` | Absolute path to the released MTK 0.28.2 `LevelUp.NavTableUpdater.Core.dll` |

The native build script currently targets macOS and needs `clang++`. The
MTK harness needs the .NET 10 SDK. None of these external inputs is committed.
The commands below assume the variables have been set for those local inputs.

```text
export TIMER_PROJECT_ROOT="$PWD"
python3 tools/prepare_tests.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/run_native_tests.py
dotnet run --project tests/mtk/Probe.csproj
```

The C# project references the released MTK 0.28.2 DLL. It tests the actual
public Core, with a local catalog containing the proposed ownership policy.
The local test catalog does not change the public catalog. Version 1 uses the
checked-in release version. Test version 2 changes the cache lifetime and helper
hash; it is an actual payload update, not a same-version repeat. That second
version is a test input and must not be released.

The matrix covers both products with every current patch selected, adding the
Timer module before and after existing managed patches, repeats, Repair,
deselection/readdition, updates to another helper version, Uninstall and
complete original Restore. It also checks standalone/MTK separation, unknown
or changed payloads, pre-execution source changes and injected final-check
failure with rollback. Retained standalone backups are explicitly permitted;
active files must return to their original bytes.

The actual archive adapter is exercised with an in-memory HTTP response.
It does not require a GitHub release to exist. X-Plane
process detection is stubbed only for these disposable fixtures; the Python
suite tests that a running X-Plane blocks the installer.

Lua tests are run by `artifacts/runtime_probe`, compiled from the native
sources under `tests/native` with the existing XLua LuaJIT library and SDK:

```text
TIMER_PROJECT_ROOT="$PWD" artifacts/runtime_probe --execute tests/runtime.lua
artifacts/runtime_probe --own "$PWD"
artifacts/runtime_probe2 --own "$PWD"
```

The Lua suite checks exact geometry outputs, all four input changes, expiry,
clock reset, signed zero, invalid inputs/clocks, original errors, the actual
loader/hooks, automatic cache removal and preservation of another wrapper.
The native harnesses use the original XLua 1 and XLua 2 callback bodies and
their `SIM_PERIOD` publication. SDK/module/GUI boundaries are stubbed; the
XLua 2 module declares legacy version 1, matching the aircraft scripts.

Benchmarks isolate two helper functions with a stub clock. They do not measure
DataRef lookup cost, flight behaviour or X-Plane FPS. Simulator validation is
still required before a public performance recommendation.

## Recorded fixture provenance

The original local verification is recorded in `RESULTS.md`. Each C# case
also records its actual input paths and SHA-256 values in a local
`original-inputs.json`. The Zibo fixture used for that run contained an
unrelated custom FMS dataref block, which had to survive; it is not claimed
as a pristine official archive. Aircraft copies, backups and raw logs are
kept under ignored `artifacts/`, not in Git.
