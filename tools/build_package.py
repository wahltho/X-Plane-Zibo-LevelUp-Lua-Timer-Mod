#!/usr/bin/env python3
"""Generate the local source manifest and integrity inventory; no publication."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wahltho.zibo-levelup-737ng.lua-timer"


def build(version="0.1.0-dev.1", previous_hashes=()):
    payloads = ["patches/load.json", "patches/distance.json", "patches/bearing.json", "payload/B738.wahltho_timer.lua"]
    def sha(relative):
        return hashlib.sha256((ROOT / "modules/lua-timer" / relative).read_bytes()).hexdigest()
    module = dict(moduleId="lua-timer", displayName="Lua Timer Mod (experimental)",
                  description="Exact-input, short-lived cache for two pure FMS geometry helpers; physics callbacks are unchanged.",
                  policy="optional", defaultEnabled=False, installationOrder=90,
                  supportedUpstreamReleases=[], requires=[], conflictsWith=[],
                  payloads=[dict(path=f, size=(ROOT / "modules/lua-timer" / f).stat().st_size, sha256=sha(f)) for f in payloads],
                  targets=[dict(operation="insert-marked-block-v1", payload=f,
                                relativePath="plugins/xlua/scripts/B738.a_fms/B738.a_fms.lua", sourceSha256=[]) for f in payloads[:3]])
    helper = payloads[-1]
    module["targets"].append(dict(operation="copy-file-v1", payload=helper,
                                  relativePath="plugins/xlua/scripts/B738.a_fms/B738.wahltho_timer.lua",
                                  sourceSha256=list(dict.fromkeys([sha(helper), *previous_hashes])), resultSha256=sha(helper)))
    manifest = dict(schemaVersion=3, packageType="compatibilityPackage", packageId=PACKAGE_ID,
                    packageVersion=version, repositoryUrl="https://github.com/wahltho/X-Plane-Zibo-LevelUp-Lua-Timer-Mod",
                    aircraftFamily="Zibo / LevelUp 737NG", supportedProducts=["zibo-737ng", "levelup-737ng"],
                    restartRequired=True, supportedUpstreamReleases=[], modules=[module])
    (ROOT / "package-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    inputs = [*("modules/lua-timer/" + f for f in payloads), "z_Install.py", "standalone_guard.py", "standalone-ownership.json", "package-manifest.json"]
    lines = ["package|id|" + PACKAGE_ID, "package|version|" + version]
    lines += [f"payload|input|{f}|size|{(ROOT / f).stat().st_size}|sha256|{hashlib.sha256((ROOT / f).read_bytes()).hexdigest()}" for f in inputs]
    (ROOT / "package-manifest.txt").write_text("\n".join(lines) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.1.0-dev.1")
    parser.add_argument("--previous-helper-sha256", action="append", default=[])
    args = parser.parse_args()
    build(args.version, args.previous_helper_sha256)
