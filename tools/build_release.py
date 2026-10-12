#!/usr/bin/env python3
"""Build a reproducible release archive from verified, explicitly listed inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from standalone_guard import verify_text_manifest


def build():
    manifest = json.loads((ROOT / "package-manifest.json").read_text())
    version = verify_text_manifest(ROOT, manifest["packageId"])
    if version != manifest["packageVersion"] or "dev" in version or "test" in version:
        raise ValueError("Release identity mismatch or test-only version")
    files = ["README.md", "LICENSE", "THIRD_PARTY.md", "z_Install.py",
             "standalone_guard.py", "standalone-ownership.json",
             "package-manifest.json", "package-manifest.txt",
             "catalog/package-entry.json", "catalog/group-member.json",
             "catalog/ownership-policy.json"]
    for module in manifest["modules"]:
        for payload in module["payloads"]:
            relative = "modules/" + module["moduleId"] + "/" + payload["path"]
            data = (ROOT / relative).read_bytes()
            if len(data) != payload["size"] or hashlib.sha256(data).hexdigest() != payload["sha256"]:
                raise ValueError("Payload mismatch: " + relative)
            files.append(relative)
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    archive = output / ("X-Plane-Zibo-LevelUp-Lua-Timer-Mod-v" + version + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
        for relative in sorted(set(files)):
            source = ROOT / relative
            if source.is_symlink() or not source.is_file():
                raise ValueError("Unsafe release input: " + relative)
            entry = zipfile.ZipInfo(relative, date_time=(2026, 10, 12, 0, 0, 0))
            entry.create_system = 3
            mode = 0o100755 if relative == "z_Install.py" else 0o100644
            entry.external_attr = mode << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            zip_file.writestr(entry, source.read_bytes(), compresslevel=9)
    external_manifest = output / "package-manifest.json"
    shutil.copyfile(ROOT / "package-manifest.json", external_manifest)
    (output / "SHA256SUMS.txt").write_text("".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n"
        for path in (archive, external_manifest)))
    print(archive)
    return archive


if __name__ == "__main__":
    build()
