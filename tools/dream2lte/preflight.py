#!/usr/bin/env python3
"""Read-only Galaxy S8+ Exynos/TWRP hardware checks. No writes or flashes."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def adb(command: str) -> str:
    result = subprocess.run(['adb', 'shell', command], capture_output=True,
                            text=True, check=False, timeout=20)
    if result.returncode:
        raise RuntimeError(f'adb shell failed for {command!r}: {result.stderr.strip()}')
    return result.stdout.strip()


def run_check() -> dict:
    try:
        model = adb('getprop ro.product.model')
        device = adb('getprop ro.product.device')
        board = adb('getprop ro.product.board')
        soc = adb('getprop ro.board.platform')
        boot = adb('readlink -f /dev/block/platform/11120000.ufs/by-name/BOOT')
        data = adb('readlink -f /dev/block/platform/11120000.ufs/by-name/USERDATA')
        bsize = adb('blockdev --getsize64 /dev/block/platform/11120000.ufs/by-name/BOOT')
        dsize = adb('blockdev --getsize64 /dev/block/platform/11120000.ufs/by-name/USERDATA')
        cmdline = adb('cat /proc/cmdline')
    except FileNotFoundError as exc:
        raise RuntimeError('adb not installed or missing from PATH') from exc
    found_fb = re.search(r'\bs3cfb\.bootloaderfb=(0x[0-9a-fA-F]+)', cmdline)
    info = {
        'model': model,
        'device': device,
        'board': board,
        'soc': soc,
        'boot_partition': boot,
        'userdata_partition': data,
        'boot_bytes': bsize,
        'userdata_bytes': dsize,
        'sboot_framebuffer': found_fb.group(1) if found_fb else None,
        'notes': ['Device checks are read-only.',
                  'This cannot validate every memory carve-out or panel variant.',
                  'No device image has been written.'],
    }
    issues = []
    if not any(k in device.lower() for k in ('dream2lte', 'dream2ltexx')):
        issues.append('ro.product.device is not dream2lte (TWRP may expose unexpected properties)')
    if model and model.upper() not in ('SM-G955F', 'SM-G955FD'):
        issues.append('model not explicitly SM-G955F/SM-G955FD (Exynos)')
    if soc and not any(tag in soc.lower() for tag in ('8895', 'exynos')):
        issues.append('ro.board.platform is not identifiable as Exynos 8895')
    if boot == data or not re.fullmatch(r'/dev/block/(?:sd[a-z]+\d+|mmcblk\d+p\d+)', boot):
        issues.append('BOOT partition path is invalid or ambiguous')
    if not re.fullmatch(r'/dev/block/(?:sd[a-z]+\d+|mmcblk\d+p\d+)', data):
        issues.append('USERDATA partition path is invalid or ambiguous')
    try:
        if int(bsize) < 16 * 1024 * 1024 or int(dsize) < 4 * 1024**3:
            issues.append('partition sizes look unreasonable')
    except ValueError:
        issues.append('could not parse partition sizes')
    if found_fb and int(found_fb.group(1), 16) != 0xcc000000:
        issues.append('framebuffer is NOT at the address hardcoded by the S8 XNU loader')
    info['issues'] = issues
    info['result'] = 'REQUIRES MANUAL REVIEW' if issues else 'MATCHES INITIAL EXPECTATIONS (NOT FLASH APPROVAL)'
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--json', type=Path, help='save a local JSON report (no serial numbers)')
    args = ap.parse_args()
    try:
        data = run_check()
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        ap.error(str(e))
    print(json.dumps(data, indent=2, ensure_ascii=False))
    if args.json:
        args.json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if data['issues']:
        raise SystemExit(3)


if __name__ == '__main__':
    main()
