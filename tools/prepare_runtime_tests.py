#!/usr/bin/env python3
"""Prepare Lua test inputs from the checked-in structural patch descriptions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    patches = [json.loads((ROOT / "modules/lua-timer/patches" / name).read_text())
               for name in ("load.json", "distance.json", "bearing.json")]
    (output / "pure-functions.lua").write_text(
        "\n\n".join("\n".join(patch["anchorLines"]) for patch in patches[1:]) + "\n")
    (output / "installation-blocks.lua").write_text(
        "\n\n".join("\n".join(patch["contentLines"]) for patch in patches) + "\n")


if __name__ == "__main__":
    prepare()
