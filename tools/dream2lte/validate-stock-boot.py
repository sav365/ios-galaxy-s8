#!/usr/bin/env python3
"""Read-only sanity check of a Samsung legacy BOOT image for S8+ bring-up.

Multi-device kernels (such as hadesKernel) contain DTBs for S8+, S8, Note8.
Select a matching FDT root /model or /compatible, never reject just because
another board appears in the same Samsung DTBH section.
"""
import argparse
import hashlib
from pathlib import Path
import struct

FDT_MAGIC = b'\xd0\x0d\xfe\xed'


def fdt_root_properties(data: bytes) -> dict[str, bytes]:
    """Parse only top-level FDT properties without external libraries."""
    if len(data) < 40 or data[:4] != FDT_MAGIC:
        raise ValueError('invalid FDT header')
    (magic, total, struct_off, strings_off, reserved_off, version, last_ver,
     boot_cpu, strings_len, struct_len) = struct.unpack_from('>10I', data)
    if total > len(data) or total < 72 or struct_off + struct_len > total or strings_off + strings_len > total:
        raise ValueError('FDT offsets outside DTB')
    strings = data[strings_off:strings_off + strings_len]
    s = data[struct_off:struct_off + struct_len]
    if len(s) < 8 or struct.unpack_from('>I', s)[0] != 1:
        raise ValueError('FDT missing root node')
    # Root node name (typically an empty NUL string), padded to 4 bytes.
    end = s.find(b'\x00', 4)
    if end < 0:
        raise ValueError('FDT malformed root name')
    at = (end + 4) & ~3
    props: dict[str, bytes] = {}
    while at + 4 <= len(s):
        tok, = struct.unpack_from('>I', s, at)
        at += 4
        if tok == 3:  # FDT_PROP
            if at + 8 > len(s):
                raise ValueError('FDT truncated property')
            length, name_off = struct.unpack_from('>II', s, at)
            at += 8
            if at + length > len(s) or name_off >= len(strings):
                raise ValueError('FDT invalid property length/name')
            name_end = strings.find(b'\x00', name_off)
            if name_end < 0:
                raise ValueError('FDT missing property name terminator')
            name = strings[name_off:name_end].decode('ascii', errors='replace')
            props[name] = s[at:at+length]
            at = (at + length + 3) & ~3
        elif tok == 4:  # FDT_NOP
            continue
        elif tok in (1, 2, 9):  # first child / end of root / end FDT
            return props
        else:
            raise ValueError('unknown FDT token in root')
    return props


def matching_devices(dt: bytes) -> list[str]:
    names = []
    start = 0
    while True:
        off = dt.find(FDT_MAGIC, start)
        if off < 0:
            break
        start = off + 4
        try:
            if off + 40 > len(dt):
                continue
            total, = struct.unpack_from('>I', dt, off + 4)
            if not 72 <= total <= len(dt) - off:
                continue
            root = fdt_root_properties(dt[off:off + total])
            model = root.get('model', b'').split(b'\0')[0].decode('ascii', 'replace')
            compatible = root.get('compatible', b'').replace(b'\0', b', ').decode('ascii', 'replace')
            if model or compatible:
                names.append(model or compatible)
        except (struct.error, ValueError):
            continue
    return names


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 0x660 or data[:8] != b'ANDROID!':
        raise ValueError('not a Samsung legacy BOOT image')
    ksz, kaddr, rsz, raddr, ssz, saddr, tags, page, dtsz, osver = struct.unpack_from('<10I', data, 8)
    if page not in (2048, 4096, 8192, 16384):
        raise ValueError('unexpected Android boot page size')
    if not 0 < ksz < 80 * 1024 * 1024:
        raise ValueError('invalid kernel length')
    if not 0 < dtsz < 16 * 1024 * 1024:
        raise ValueError('no usable Samsung DTBH in this BOOT image')
    def pages(n):
        return (n + page - 1) // page * page
    off = page + pages(ksz) + pages(rsz) + pages(ssz)
    if off + dtsz > len(data) or data[off:off+4] != b'DTBH':
        raise ValueError('DTBH section not found at expected offset')
    dt = data[off:off + dtsz]
    devices = matching_devices(dt)
    if not devices:
        raise ValueError('DTBH contains no valid FDT board descriptions')
    # Samsung may call the S8+ board either SM-G955F or dream2lte.
    if not any('SM-G955' in d.upper() or 'DREAM2LTE' in d.upper() for d in devices):
        raise ValueError('DTBH has no Galaxy S8+ (SM-G955/dream2lte) board description')
    return dict(sha256=hashlib.sha256(data).hexdigest(), size=len(data), page=page,
                kernel_size=ksz, ramdisk_size=rsz, dt_size=dtsz,
                kernel_address=f'{kaddr:#x}', dtb_models=devices)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stock_boot', type=Path, help='readable BOOT backup from your Galaxy S8+')
    args = ap.parse_args()
    try:
        details = inspect(args.stock_boot)
    except (OSError, ValueError) as e:
        ap.error(str(e))
    for k, v in details.items():
        print(f'{k}: {v}')
    print('WARNING: identifying an S8+ DTB does NOT prove that this image came from your phone.')
    print('Use a BOOT backup read from the G955F/G955FD phone being tested.')


if __name__ == '__main__':
    main()
