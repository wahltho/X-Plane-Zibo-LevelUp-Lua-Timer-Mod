#!/usr/bin/env python3
"""Prepare disposable package versions and groups from verified local caches."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
from prepare_runtime_tests import prepare as prepare_runtime

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def prepare():
    required = ('TIMER_MTK_CHECKOUT', 'TIMER_PACKAGE_EVIDENCE')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit('Set ' + ', '.join(missing) + '; see tests/README.md')
    mtk = Path(os.environ['TIMER_MTK_CHECKOUT']).expanduser().resolve()
    evidence = Path(os.environ['TIMER_PACKAGE_EVIDENCE']).expanduser().resolve()
    ART.mkdir(exist_ok=True)
    catalog = json.loads((mtk / 'catalog/content-package-catalog.json').read_text())
    member = json.loads((ROOT / 'catalog/group-member.json').read_text())
    if not any(entry['packageId'] == member['packageId'] for entry in catalog['packages']):
        catalog['packages'].append(json.loads((ROOT / 'catalog/package-entry.json').read_text()))
    policy = json.loads((ROOT / 'catalog/ownership-policy.json').read_text())
    if not any(entry['packageId'] == member['packageId'] for entry in catalog['ownershipPolicies']):
        catalog['ownershipPolicies'].append(policy)
    for entry in catalog['packages']:
        if entry['packageId'] in ('wahltho.zibo-40535.maintenance', 'wahltho.levelup-737ng.maintenance'):
            if not any(item['moduleId'] == member['moduleId'] for item in entry['members']):
                entry['members'].append(member)
    dump(ART / 'dev-catalog.json', catalog)
    helper_hash = hashlib.sha256((ROOT / 'modules/lua-timer/payload/B738.wahltho_timer.lua').read_bytes()).hexdigest()
    release_version = json.loads((ROOT / 'package-manifest.json').read_text())['packageVersion']
    for suffix, version in (('v1', release_version), ('v2', release_version + '-test.2')):
        output = ART / ('package-' + suffix)
        if output.exists():
            shutil.rmtree(output)
        output.mkdir()
        for name in ('modules', 'catalog', 'tools'):
            shutil.copytree(ROOT / name, output / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('standalone_guard.py', 'standalone-ownership.json', 'z_Install.py'):
            shutil.copy2(ROOT / name, output / name)
        if suffix == 'v2':
            helper = output / 'modules/lua-timer/payload/B738.wahltho_timer.lua'
            helper.write_bytes(helper.read_bytes().replace(b'local age = 0.05', b'local age = 0.04'))
        spec = importlib.util.spec_from_file_location('test_builder_' + suffix, output / 'tools/build_package.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        timer = builder.build(version, [helper_hash] if suffix == 'v2' else [])
        for product in ('zibo-737ng', 'levelup-737ng'):
            group = Path((evidence / 'inputs' / (product + '-group-path.txt')).read_text().strip())
            destination = ART / (product + '-' + suffix)
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(group, destination)
            manifest = json.loads((destination / 'package-manifest.json').read_text())
            manifest['modules'].extend(timer['modules'])
            manifest['packageVersion'] += '-timer-' + suffix
            manifest['sources'].append(dict(packageId=timer['packageId'], moduleId='lua-timer', releaseTag=version,
                                            assetSha256=hashlib.sha256((output / 'package-manifest.json').read_bytes()).hexdigest(),
                                            repositoryUrl=timer['repositoryUrl']))
            dump(destination / 'package-manifest.json', manifest)
            shutil.copytree(output / 'modules/lua-timer', destination / 'modules/lua-timer')
    prepare_runtime()


if __name__ == '__main__':
    prepare()
