#!/usr/bin/env python3
"""
epw_tool.py - inspect and rebuild EaglercraftX .epw asset bundles.

The .epw ("Eaglercraft Package for Web") file is a flat container:

    offset  0   u32   magic 0x2447B045  ("E.G$" little-endian)
    offset  4   u32   magic 0x4D5A4757
    offset  8   u32   total file length (must equal len(file))
    offset 24   u32   start of the data region (end of header)
    ...         section descriptors, each  {u32 offset, u32 clen, u32 ulen, u32 flags}
    offset 384  ..    NUL-terminated string table, then the section payloads

Every large section payload is a raw .xz stream. The section describing
"assets.epk" holds the game's whole resource tree in lax1dude's EPK v2.0
format:

    "EAGPKG$$" <u8 len>"ver2.0" <u8 len>name 0x00 'R' <comment> ... 0x00
    then a chain of records:
        ":>"  4-char type  <u8 len>name  u32 size  u32 crc32  data
    where size == 4 (the crc) + len(data) + 1 (the ':' opening the next
    record), and the chain ends with ":>END$:::YEE:>".

Subcommands:
    list    <epw>                       print every EPK entry
    extract <epw> <outdir>              unpack the EPK to a directory
    patch   <epw> <packdir> <out.epw>   overlay a resource pack's textures
"""

import os
import struct
import sys
import lzma
import zlib

MAGIC_A = 608649541
MAGIC_B = 1297301847

# Section descriptors that carry an xz payload, as {header offset: label}.
# Only ASSETS_SECTION is rewritten; the others are copied through verbatim.
ASSETS_SECTION = 292
SECTION_OFFSETS = (196, 212, 228, 244, 260, 292, 324)

EPK_MAGIC = b"EAGPKG$$"
EPK_END = b":>END$:::YEE:>"


# ---------------------------------------------------------------- EPW layout

def read_epw(path):
    data = open(path, "rb").read()
    a, b, total = struct.unpack_from("<3I", data, 0)
    if (a, b) != (MAGIC_A, MAGIC_B):
        raise ValueError("not an EPW file")
    if total != len(data):
        raise ValueError("EPW length field %d != actual %d" % (total, len(data)))
    return data


def sections(data):
    """Yield (header_offset, offset, clen, ulen, flags) sorted by payload offset."""
    out = []
    for h in SECTION_OFFSETS:
        off, clen, ulen, flags = struct.unpack_from("<4I", data, h)
        out.append((h, off, clen, ulen, flags))
    return sorted(out, key=lambda s: s[1])


def find_assets_epk(data):
    off, clen, ulen, _flags = struct.unpack_from("<4I", data, ASSETS_SECTION)
    epk = lzma.decompress(data[off:off + clen])
    if not epk.startswith(EPK_MAGIC):
        raise ValueError("section at %d is not an EPK" % ASSETS_SECTION)
    if len(epk) != ulen:
        raise ValueError("EPK decompressed to %d, header says %d" % (len(epk), ulen))
    return epk


# ----------------------------------------------------------------- EPK codec

def epk_parse(epk):
    """Return (prologue_bytes, [(type, name, data)])."""
    start = epk.index(b":>")
    entries = []
    i = start
    while True:
        if epk[i:i + 2] != b":>":
            raise ValueError("lost record alignment at %d" % i)
        kind = epk[i + 2:i + 6]
        if kind == b"END$":
            break
        p = i + 6
        nlen = epk[p]
        p += 1
        name = epk[p:p + nlen].decode("utf-8")
        p += nlen
        size, crc = struct.unpack_from(">2I", epk, p)
        p += 8
        payload = epk[p:p + size - 5]
        if zlib.crc32(payload) & 0xFFFFFFFF != crc:
            raise ValueError("crc mismatch on %s" % name)
        entries.append((kind, name, payload))
        i = p + size - 5
    return epk[:start], entries


def epk_build(prologue, entries):
    out = [prologue]
    for kind, name, payload in entries:
        raw = name.encode("utf-8")
        if len(raw) > 255:
            raise ValueError("name too long: %s" % name)
        out.append(b":>" + kind + bytes([len(raw)]) + raw)
        out.append(struct.pack(">2I", len(payload) + 5,
                               zlib.crc32(payload) & 0xFFFFFFFF))
        out.append(payload)
    out.append(EPK_END)
    return b"".join(out)


def xz(payload):
    """Compress the way the original bundle does: LZMA2, CRC32 stream check."""
    return lzma.compress(
        payload,
        format=lzma.FORMAT_XZ,
        check=lzma.CHECK_CRC32,
        filters=[{"id": lzma.FILTER_LZMA2, "preset": 6}],
    )


def write_epw(data, new_epk, out_path):
    """Splice a rebuilt EPK back in and repair every offset it moves."""
    blob = xz(new_epk)
    old_off, old_clen, _old_ulen, flags = struct.unpack_from("<4I", data, ASSETS_SECTION)
    delta = len(blob) - old_clen

    buf = bytearray(data[:old_off] + blob + data[old_off + old_clen:])
    struct.pack_into("<4I", buf, ASSETS_SECTION,
                     old_off, len(blob), len(new_epk), flags)

    # Any section stored after the one we replaced slides by delta.
    for h, off, clen, ulen, f in sections(data):
        if h != ASSETS_SECTION and off > old_off:
            struct.pack_into("<4I", buf, h, off + delta, clen, ulen, f)

    struct.pack_into("<I", buf, 8, len(buf))
    open(out_path, "wb").write(buf)
    return len(blob), delta


# ------------------------------------------------------------------ commands

def cmd_list(epw_path):
    entries = epk_parse(find_assets_epk(read_epw(epw_path)))[1]
    for _kind, name, payload in entries:
        print("%9d  %s" % (len(payload), name))
    print("%d entries" % len(entries))


def cmd_extract(epw_path, outdir):
    entries = epk_parse(find_assets_epk(read_epw(epw_path)))[1]
    for _kind, name, payload in entries:
        dest = os.path.join(outdir, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(payload)
    print("extracted %d entries to %s" % (len(entries), outdir))


def collect_pack(packdir):
    """Map EPK path -> bytes for every texture file in a resource pack."""
    root = os.path.join(packdir, "assets", "minecraft", "textures")
    found = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not (fn.endswith(".png") or fn.endswith(".mcmeta")):
                continue
            full = os.path.join(dirpath, fn)
            key = os.path.relpath(full, packdir).replace(os.sep, "/")
            found[key] = open(full, "rb").read()
    return found


def cmd_patch(epw_path, packdir, out_path):
    data = read_epw(epw_path)
    prologue, entries = epk_parse(find_assets_epk(data))
    pack = collect_pack(packdir)

    existing = {name for _k, name, _d in entries}
    replaced = added = identical = 0
    out = []
    for kind, name, payload in entries:
        if name in pack:
            if pack[name] == payload:
                identical += 1
            else:
                payload = pack[name]
                replaced += 1
        out.append((kind, name, payload))

    # A .mcmeta can be new even when its .png already existed - without it an
    # animated texture with a different frame count renders as a static strip.
    for name in sorted(pack):
        if name in existing or not name.endswith(".mcmeta"):
            continue
        if name[:-len(".mcmeta")] in existing:
            out.append((b"FILE", name, pack[name]))
            added += 1

    new_epk = epk_build(prologue, out)
    clen, delta = write_epw(data, new_epk, out_path)
    unused = len(pack) - replaced - added - identical
    print("replaced %d textures, %d already identical, added %d mcmeta, "
          "%d pack files absent from the bundle"
          % (replaced, identical, added, unused))
    print("epk %d -> %d bytes, xz %d bytes (%+d), wrote %s"
          % (len(find_assets_epk(data)), len(new_epk), clen, delta, out_path))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "list" and len(argv) == 3:
        cmd_list(argv[2])
    elif cmd == "extract" and len(argv) == 4:
        cmd_extract(argv[2], argv[3])
    elif cmd == "patch" and len(argv) == 5:
        cmd_patch(argv[2], argv[3], argv[4])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
