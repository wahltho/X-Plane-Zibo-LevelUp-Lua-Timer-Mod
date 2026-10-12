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
