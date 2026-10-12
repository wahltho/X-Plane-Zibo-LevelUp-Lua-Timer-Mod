#!/usr/bin/env python3
"""Compile test harnesses and exercise both XLua callback implementations."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'


def run(arguments, log):
    with (ART / log).open('w') as stream:
        subprocess.run(arguments, cwd=ROOT, env={**os.environ, 'TIMER_PROJECT_ROOT': str(ROOT)},
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def main():
    if not os.environ.get('TIMER_XLUA_CHECKOUT'):
        raise SystemExit('Set TIMER_XLUA_CHECKOUT; see tests/README.md')
    xlua = Path(os.environ['TIMER_XLUA_CHECKOUT']).expanduser().resolve()
    ART.mkdir(exist_ok=True)
    common = ['clang++', '-std=c++17', '-DAPL=1', '-DIBM=0', '-DLIN=0',
              '-I' + str(xlua / 'lua_sdk'), '-I' + str(xlua / 'SDK/CHeaders/XPLM')]
    library = str(xlua / 'lua_sdk/libluajit_mac.a')
    run([*common, 'tests/native/probe.cpp', 'tests/native/xptimers.cpp', 'tests/native/lua_helpers.cpp',
         library, '-o', str(ART / 'runtime_probe')], 'native-build.txt')
    run([*common, '-DMOBILE=1', 'tests/native/probe2.cpp', 'tests/native/xptimers.cpp',
         'tests/native/lua_helpers_without_setup.cpp', 'tests/native/setup2.cpp', library,
         '-o', str(ART / 'runtime_probe2')], 'native-build2.txt')
    run([str(ART / 'runtime_probe'), '--execute', 'tests/runtime.lua'], 'runtime.txt')
    run([str(ART / 'runtime_probe'), '--own', str(ROOT)], 'native-runtime.txt')
    run([str(ART / 'runtime_probe2'), '--own', str(ROOT)], 'native-runtime2.txt')


if __name__ == '__main__':
    main()
