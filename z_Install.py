#!/usr/bin/env python3
"""Install, update or uninstall the independent Lua calculation cache."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from standalone_guard import Guard, OwnershipError, safe, verify_text_manifest

PACKAGE = Path(__file__).resolve().parent
PACKAGE_ID = "wahltho.zibo-levelup-737ng.lua-timer"
FMS = "plugins/xlua/scripts/B738.a_fms/B738.a_fms.lua"
HELPER = "plugins/xlua/scripts/B738.a_fms/B738.wahltho_timer.lua"
PATCHES = ("load.json", "distance.json", "bearing.json")


def decode(data):
    bom = data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    # Do not normalize mixed line endings and lose unrelated original bytes.
    if "\r" in text.replace("\r\n", ""):
        raise OwnershipError("Unsupported bare CR line ending")
    if "\r\n" in text and "\n" in text.replace("\r\n", ""):
        raise OwnershipError("Mixed line endings: no files changed")
    eol = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), eol, bom


def transform(data, uninstall=False):
    text, eol, bom = decode(data)
    for name in PATCHES:
        patch = json.loads((PACKAGE / "modules/lua-timer/patches" / name).read_text())
        block = "\n".join([patch["beginMarker"], *patch["contentLines"], patch["endMarker"]])
        anchor = "\n".join(patch["anchorLines"])
        # Verify the complete pure helper body, even on repeat and uninstall.
        if text.count(anchor) != 1:
            raise OwnershipError("Unsupported or modified calculation: " + patch["name"])
        if patch["beginMarker"] in text or patch["endMarker"] in text:
            if text.count(block) != 1:
                raise OwnershipError("Modified Timer Mod block: " + patch["name"])
            if uninstall:
                text = text.replace("\n" + block, "", 1)
        elif not uninstall:
            text = text.replace(anchor, anchor + "\n" + block, 1)
        else:
            raise OwnershipError("Installed Timer Mod block is missing: " + patch["name"])
    if re.search(r"\b(?:timed_before_physics|timed_after_physics)\b", text):
        raise OwnershipError("Legacy Timer Mod callbacks found; restore their verified backups first")
    return (b"\xef\xbb\xbf" if bom else b"") + text.replace("\n", eol).encode("utf-8")


def run(root, uninstall=False):
    version = verify_text_manifest(PACKAGE, PACKAGE_ID)
    manifest = json.loads((PACKAGE / "package-manifest.json").read_text())
    # Require the input inventory to cover every installer and runtime input.
    inventory = (PACKAGE / "package-manifest.txt").read_text()
    for relative in ("z_Install.py", "standalone_guard.py", "standalone-ownership.json",
                     "package-manifest.json", "modules/lua-timer/payload/B738.wahltho_timer.lua",
                     *("modules/lua-timer/patches/" + p for p in PATCHES)):
        if not any(line.split("|")[2:3] == [relative] for line in inventory.splitlines()):
            raise OwnershipError("Package inventory omits " + relative)
    if manifest["packageId"] != PACKAGE_ID or manifest["packageVersion"] != version:
        raise OwnershipError("Inconsistent package identity/version")
    with Guard(root, PACKAGE) as guard:
        source = safe(guard.root, FMS).read_bytes()
        if uninstall:
            if guard.state is None:
                raise OwnershipError("No verified standalone installation to uninstall")
            transformed = transform(source, True)
            original = guard.original_payload(FMS)
            # Keep later edits outside our marked blocks, never copy a stale
            # whole-file backup over another patch. Original bytes are verified
            # by Guard; an unchanged source restores byte-for-byte.
            if transformed == original:
                transformed = original
            changes = {FMS: transformed, HELPER: guard.original_payload(HELPER)}
        else:
            changes = {FMS: transform(source), HELPER: (PACKAGE / "modules/lua-timer/payload/B738.wahltho_timer.lua").read_bytes()}
        guard.apply(changes, uninstall=uninstall, version=version)
    return "Uninstalled" if uninstall else "Installed/updated"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "update", "uninstall"))
    parser.add_argument("--aircraft-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(run(args.aircraft_root, args.action == "uninstall"))
        print("Restart X-Plane. Other patches and physics callbacks were retained.")
    except (OwnershipError, OSError, ValueError) as error:
        parser.exit(1, "Blocked: " + str(error) + "\n")


if __name__ == "__main__":
    main()
