# Verification — 12 October 2026

The local development package is implemented and verified against released
MTK Core 0.28.2 and both current catalog patch groups. Nothing was published
or installed into an actual aircraft.

| Check | Result |
| --- | --- |
| Standalone installer | 19 tests passed; includes 16 product/EOL/BOM/final-newline combinations |
| Lua runtime | 54,434 assertions passed using the actual XLua LuaJIT library |
| XLua 1 callback/period harness | 35 assertions passed |
| XLua 2 legacy-script callback/period harness | 35 assertions passed |
| Production MTK lifecycle and archive adapter | 19 distinct cases passed across Zibo and LevelUp |
| Fully patched FMS, Tablet, Calc and helper syntax | All eight files accepted by LuaJIT/Lua 5.1 |
| Package inventory and whitespace check | Passed |

The native matrix covers 10, 20, 30, 60 and 120 FPS, normal before/after phases,
frame-normalized loading, replay, zero-period pause and a long frame. The
FMS callback tails and all existing `SIM_PERIOD` references are also compared
before and after applying the package.

The MTK cases use VNAV, FANS CDU, Tablet Performance, W&B, Auto Jetway, CPDLC,
VREF, 27K/SFP, Intentional Fixes and GSE wherever offered for that product.
They cover both installation orders, each optional module's deselection and
readdition with Timer present, an actual helper-version update, repeats,
Repair, Uninstall and byte-exact original Restore.

Unknown or modified helpers and namespaces, standalone ownership and changes
after planning block without changing the aircraft. An injected final-scope
verification failure occurs after the writes and rolls the complete operation
back. The normal standalone rollback is tested independently.

Two test-harness issues were corrected after the first full run. Its uninstall
snapshot initially treated retained private backups as unexpected files.
Those backups must remain; the corrected test permits only private backup
paths and still requires every active file to be restored. The first failure
fixture prevented state reading before execution, so it could not prove
rollback. It was replaced by an injected final-check failure after mutation.
The final matrix combines 14 unchanged full-run passes with five targeted
passes, including the actual archive adapter. Raw runs are retained.

Isolated 300,000-call benchmarks with LuaJIT disabled showed roughly 35–40%
less time for identical inputs. With changing inputs, adaptive cache removal
returned execution to approximately the original cost. This uses a stub clock
and excludes actual DataRef access; it is not an X-Plane FPS measurement.

Simulator flight behaviour, real cache hit rates and FPS gains remain open.
The implementation deliberately does not schedule complete scripts at 20 Hz.

Machine-readable results and source hashes are retained locally in
`artifacts/verification-results.json`; aircraft fixtures, backups and raw
logs are excluded from the repository. The public MTK catalog and existing
patch repositories were not changed. Catalog policy publication is required
before distributing this new optional patch.

## Repository preparation recheck

The test runners now take their external paths from environment variables.
After that change, all 19 standalone tests, 54,434 Lua assertions and both
35-assertion native callback suites passed again. The complete 19-case MTK
matrix then passed in one fresh run with zero failures, including both
products' module selection, helper-version update, Restore and rollback.
This fresh run does not depend on combining earlier partial runs.

The source package inventory, payload hashes and catalog templates were
checked again. GitHub Actions also passed its package-integrity and Lua
runtime checks on Linux. No aircraft fixtures or compiled libraries were
pushed, and no release or public catalog change was made. Simulator flight
and performance validation remain open.

Fresh local lifecycle evidence:
`artifacts/mtk-run-0e4cf8162a944984a16917f4262de506/logs/results.json`.

## First Beta release verification

The release package is now `0.1.0-beta.1`. The four Lua/patch payloads and the
standalone installer logic are unchanged from the verified development build.
The test preparation uses the checked-in release version and a separate,
unpublished helper update to exercise the upgrade path.

Before publication, all 19 standalone tests, 54,434 Lua assertions and both
35-assertion native callback suites passed again. All 19 MTK lifecycle cases
also passed in one fresh run against released Core 0.28.2.0, with the local
test catalog based on catalog 1.20.0 plus the Timer ownership policy. This
includes both products, the existing patch groups, genuine helper updates,
Repair, selection changes, byte-exact Restore and rollback after writes.

Fresh lifecycle evidence: `artifacts/mtk-run-a9e34b2d04d74550a9ff3ce07b757647/logs/results.json`.

The release ZIP has 15 explicitly listed files. Its manifest, payload sizes
and SHA-256 values were verified, and two builds produced identical archives.
The final MTK catalog and UI tests passed: 852 tests, with six local platform
skips; CI passed on Linux, Windows and macOS, including the applicable
platform checks. The ownership policy was published in catalog 1.21.0 before
the patch was made available. Catalog 1.22.0 adds its optional group entries.

Simulator flight behaviour and FPS validation remain open. This is a Beta
release without a promised performance gain.
