import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import z_Install as installer
import standalone_guard as guard_module

def fixture(name):
    if not os.environ.get(name):
        raise RuntimeError('Set ' + name + '; see tests/README.md')
    root = Path(os.environ[name]).expanduser().resolve()
    if not (root / installer.FMS).is_file():
        raise RuntimeError(name + ' does not contain ' + installer.FMS)
    return root


ZIBO = fixture('TIMER_ZIBO_AIRCRAFT')
LEVELUP = fixture('TIMER_LEVELUP_SCRIPTS')


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'artifacts').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'aircraft'
        self.target = self.root / installer.FMS
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes((ZIBO / installer.FMS).read_bytes())
        self.original = self.target.read_bytes()
        self.processes = mock.patch.object(guard_module.subprocess, 'run', return_value=mock.Mock(stdout=''))
        self.processes.start(); self.addCleanup(self.processes.stop)
        self.states = mock.patch.object(guard_module, 'state_candidates', return_value=[])
        self.states.start(); self.addCleanup(self.states.stop)

    def install(self):
        installer.run(self.root)

    def receipt(self):
        return self.root / '.patch-ownership' / installer.PACKAGE_ID / 'receipt.json'

    def blocked(self, action=None):
        before = snapshot(self.root)
        with self.assertRaises((guard_module.OwnershipError, OSError)):
            (action or self.install)()
        self.assertEqual(before, snapshot(self.root))

    def test_products_line_endings_bom_and_final_newline(self):
        for product in (ZIBO, LEVELUP):
            for eol in (b'\n', b'\r\n'):
                for bom in (b'', b'\xef\xbb\xbf'):
                    for final in (True, False):
                        with self.subTest(product=product, eol=eol, bom=bom, final=final):
                            source = (product / installer.FMS).read_bytes().replace(b'\r\n', b'\n').rstrip(b'\n')
                            source = bom + source.replace(b'\n', eol) + (eol if final else b'')
                            installed = installer.transform(source)
                            self.assertEqual(installer.transform(installed, True), source)
                            self.assertEqual(installer.transform(installed), installed)
                            self.assertEqual(installed.startswith(b'\xef\xbb\xbf'), bool(bom))
                            if eol == b'\r\n': self.assertNotIn(b'\n', installed.replace(b'\r\n', b''))

    def test_install_repeat_and_exact_uninstall(self):
        self.target.chmod(0o640)
        self.install(); installed = self.target.read_bytes()
        receipt = json.loads(self.receipt().read_text())
        backup = self.root / receipt['files'][installer.FMS]['backupRelativePath']
        self.assertEqual(backup.read_bytes(), self.original)
        self.install(); self.assertEqual(self.target.read_bytes(), installed)
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)
        installer.run(self.root, True)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse((self.root / installer.HELPER).exists())
        self.assertFalse(self.receipt().exists())
        self.assertEqual(backup.read_bytes(), self.original)

    def test_uninstall_preserves_later_unrelated_patch(self):
        self.install()
        self.target.write_bytes(self.target.read_bytes() + (b'\r\n-- unrelated custom patch\r\n' if b'\r\n' in self.original else b'\n-- unrelated custom patch\n'))
        installer.run(self.root, True)
        self.assertEqual(self.target.read_bytes(), self.original + (b'\r\n-- unrelated custom patch\r\n' if b'\r\n' in self.original else b'\n-- unrelated custom patch\n'))

    def test_unknown_body(self):
        self.target.write_bytes(self.original.replace(b'3440.064795', b'3440.064796'))
        self.blocked()

    def test_legacy_timer(self):
        self.target.write_bytes(self.original.replace(b'function after_physics()', b'function timed_after_physics()'))
        self.blocked()

    def test_duplicate_anchor(self):
        self.target.write_bytes(self.original + b'\njit.off()\n')
        self.blocked()

    def test_unknown_namespace(self):
        self.target.write_bytes(self.original + b'\n-- BEGIN WAHLTHO_LUA_TIMER UNKNOWN\n-- END WAHLTHO_LUA_TIMER UNKNOWN\n')
        self.blocked()

    def test_identical_unowned_payload(self):
        (self.root / installer.HELPER).write_bytes((ROOT / 'modules/lua-timer/payload/B738.wahltho_timer.lua').read_bytes())
        self.blocked()

    def test_manual_markers_without_owner(self):
        self.target.write_bytes(installer.transform(self.original))
        self.blocked()

    def test_modified_owned_markers(self):
        self.install()
        self.target.write_bytes(self.target.read_bytes().replace(b'wahltho_timer_cache.wrap4', b'wahltho_timer_cache.changed'))
        self.blocked(); self.blocked(lambda: installer.run(self.root, True))

    def test_corrupt_original_backup(self):
        self.install()
        receipt = json.loads(self.receipt().read_text())
        (self.root / receipt['files'][installer.FMS]['backupRelativePath']).write_bytes(b'corrupt')
        self.blocked(); self.blocked(lambda: installer.run(self.root, True))

    def test_modified_payload(self):
        self.install(); (self.root / installer.HELPER).write_bytes(b'changed')
        self.blocked(); self.blocked(lambda: installer.run(self.root, True))

    def test_symlink(self):
        self.target.unlink(); self.target.symlink_to(ZIBO / installer.FMS)
        self.blocked()

    def test_missing_receipt_uninstall(self):
        self.blocked(lambda: installer.run(self.root, True))

    def test_incomplete_transaction(self):
        journal = self.receipt().parent / 'transaction'; journal.mkdir(parents=True)
        (journal / 'journal.json').write_text('{}')
        self.blocked()

    def test_mtk_owned_file(self):
        state = Path(self.temp.name) / 'state.json'
        state.write_text(json.dumps(dict(SchemaVersion=7, ContentInstallations={str(self.root):dict(AircraftFolder=str(self.root), ContentComponents={'group':dict(Files=[dict(RelativePath=installer.FMS)])})})))
        with mock.patch.object(guard_module, 'state_candidates', return_value=[state]): self.blocked()

    def test_running_xplane(self):
        with mock.patch.object(guard_module.subprocess, 'run', return_value=mock.Mock(stdout='X-Plane')): self.blocked()

    def test_rollback_after_first_target_write(self):
        atomic = guard_module._atomic
        fired = False
        def failure(path, data, mode=0o644):
            nonlocal fired
            if path == self.root / installer.HELPER and not fired:
                fired = True; raise OSError('simulated write failure')
            return atomic(path, data, mode)
        with mock.patch.object(guard_module, '_atomic', side_effect=failure): self.blocked()

    def test_real_package_update_retains_original(self):
        self.install()
        receipt = json.loads(self.receipt().read_text())
        first_backup = (self.root / receipt['files'][installer.FMS]['backupRelativePath']).read_bytes()
        package = Path(self.temp.name) / 'next'; shutil.copytree(ROOT, package, ignore=shutil.ignore_patterns('artifacts', '__pycache__', 'bin', 'obj'))
        helper = package / 'modules/lua-timer/payload/B738.wahltho_timer.lua'
        helper.write_bytes(helper.read_bytes().replace(b'local age = 0.05', b'local age = 0.04'))
        spec = importlib.util.spec_from_file_location('next_builder', package / 'tools/build_package.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder); builder.build('0.1.0-dev.2')
        with mock.patch.object(installer, 'PACKAGE', package): installer.run(self.root)
        updated = json.loads(self.receipt().read_text())
        self.assertEqual(updated['packageVersion'], '0.1.0-dev.2')
        self.assertEqual((self.root / installer.HELPER).read_bytes(), helper.read_bytes())
        self.assertEqual((self.root / updated['files'][installer.FMS]['backupRelativePath']).read_bytes(), first_backup)
        installer.run(self.root, True)
        self.assertEqual(self.target.read_bytes(), self.original)


if __name__ == '__main__': unittest.main()
