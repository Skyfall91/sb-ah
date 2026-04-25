"""Minimal NBT decoder for Hypixel Skyblock AH item_bytes."""
from __future__ import annotations
import base64
import gzip
import struct


def _read(tag_type: int, data: bytes, i: int):
    if tag_type == 1:
        v = data[i]; return (v if v < 128 else v - 256), i + 1
    if tag_type == 2:
        return struct.unpack_from(">h", data, i)[0], i + 2
    if tag_type == 3:
        return struct.unpack_from(">i", data, i)[0], i + 4
    if tag_type == 4:
        return struct.unpack_from(">q", data, i)[0], i + 8
    if tag_type == 5:
        return struct.unpack_from(">f", data, i)[0], i + 4
    if tag_type == 6:
        return struct.unpack_from(">d", data, i)[0], i + 8
    if tag_type == 7:
        n = struct.unpack_from(">i", data, i)[0]
        return data[i + 4: i + 4 + n], i + 4 + n
    if tag_type == 8:
        n = struct.unpack_from(">H", data, i)[0]
        return data[i + 2: i + 2 + n].decode("utf-8", "ignore"), i + 2 + n
    if tag_type == 9:
        et = data[i]; n = struct.unpack_from(">i", data, i + 1)[0]; i += 5
        items = []
        for _ in range(n):
            v, i = _read(et, data, i)
            items.append(v)
        return items, i
    if tag_type == 10:
        result = {}
        while i < len(data):
            ct = data[i]; i += 1
            if ct == 0:
                break
            nl = struct.unpack_from(">H", data, i)[0]; i += 2
            name = data[i: i + nl].decode("utf-8", "ignore"); i += nl
            v, i = _read(ct, data, i)
            result[name] = v
        return result, i
    if tag_type == 11:
        n = struct.unpack_from(">i", data, i)[0]
        return [struct.unpack_from(">i", data, i + 4 + j * 4)[0] for j in range(n)], i + 4 + n * 4
    if tag_type == 12:
        n = struct.unpack_from(">i", data, i)[0]
        return [struct.unpack_from(">q", data, i + 4 + j * 8)[0] for j in range(n)], i + 4 + n * 8
    return None, i


def decode_auction_item(item_bytes_b64: str) -> tuple[int, str]:
    """
    Decode base64-gzipped NBT from Hypixel AH item_bytes.
    Returns (count, skyblock_id). Falls back to (1, '') on error.
    """
    try:
        raw = gzip.decompress(base64.b64decode(item_bytes_b64))
        # Root TAG_Compound: skip type byte (1B) + empty name (2B for len=0)
        root, _ = _read(10, raw, 3)
        item_list = root.get("i", [])
        if not item_list:
            return 1, ""
        item = item_list[0]
        count = item.get("Count", 1)
        tag = item.get("tag", {})
        extra = tag.get("ExtraAttributes", {}) if isinstance(tag, dict) else {}
        skyblock_id = extra.get("id", "") if isinstance(extra, dict) else ""
        return int(count), str(skyblock_id)
    except Exception:
        return 1, ""
