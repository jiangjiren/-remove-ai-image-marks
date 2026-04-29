#!/usr/bin/env python3
"""
Remove C2PA, AI metadata (tEXt/XMP/EXIF), and optionally invisible watermarks
from PNG/JPEG images.

Usage:
  python clean_image.py <input> [output]          # strip metadata only (fast, offline)
  python clean_image.py <input> [output] --deep   # also attempt invisible watermark removal
  python clean_image.py <input> --check           # report found AI identifiers, no changes
"""
import sys
import struct
import zlib
import os
import re
import json
import argparse

# ---------------------------------------------------------------------------
# PNG standard ancillary chunks to KEEP (everything else is stripped)
# tEXt / zTXt / iTXt are intentionally excluded — they carry AI prompts,
# workflow JSON, DigitalSourceType, and other generation metadata.
# ---------------------------------------------------------------------------
KEEP_PNG_CHUNKS = {
    'IHDR', 'IDAT', 'IEND', 'PLTE', 'tRNS',
    'cHRM', 'gAMA', 'iCCP', 'sRGB', 'bKGD',
    'hIST', 'tIME', 'pHYs', 'sBIT', 'sPLT',
}

# AI-related keywords searched inside text-type chunks
AI_KEYWORDS = [
    b'c2pa', b'C2PA', b'synthid', b'SynthID',
    b'parameters', b'workflow', b'prompt', b'seed',
    b'DigitalSourceType', b'trainedAlgorithmicMedia',
    b'midjourney', b'Midjourney', b'DALL-E', b'dall-e',
    b'stable diffusion', b'Stable Diffusion', b'comfyui', b'ComfyUI',
    b'invokeai', b'InvokeAI', b'firefly', b'Firefly',
    b'generatedBy', b'ai-generated', b'AI-generated',
    b'tc260', b'TC260', b'tc260.org', b'AIGC', b'dreamina', b'aigc_info',
]


def _read_png_chunks(data: bytes) -> list[tuple[str, int, bytes]]:
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError("Not a valid PNG file")
    pos, chunks = 8, []
    while pos < len(data):
        if pos + 12 > len(data):
            break
        length = struct.unpack('>I', data[pos:pos+4])[0]
        ctype = data[pos+4:pos+8].decode('ascii', errors='replace')
        cdata = data[pos+8:pos+8+length]
        chunks.append((ctype, length, cdata))
        pos += 12 + length
    return chunks


def _decode_itxt(cdata: bytes) -> tuple[str, str]:
    """Decode iTXt chunk, return (key, text)."""
    null = cdata.index(b'\x00')
    key = cdata[:null].decode('utf-8', errors='replace')
    rest = cdata[null+1:]
    comp_flag = rest[0]
    rest2 = rest[2:]
    null2 = rest2.index(b'\x00')
    rest3 = rest2[null2+1:]
    null3 = rest3.index(b'\x00')
    text_bytes = rest3[null3+1:]
    if comp_flag:
        text_bytes = zlib.decompress(text_bytes)
    return key, text_bytes.decode('utf-8', errors='replace')


def _decode_exif_json(cdata: bytes) -> str:
    """Extract JSON payload from eXIf chunk UserComment tag (tag 37510)."""
    try:
        # Find ASCII JSON in the raw EXIF bytes
        m = re.search(rb'\{.*\}', cdata, re.DOTALL)
        if m:
            raw = m.group(0).decode('utf-8', errors='replace')
            obj = json.loads(raw)
            return json.dumps(obj, ensure_ascii=False)
    except Exception:
        pass
    return cdata[:80].hex()


def _chunk_text_preview(ctype: str, cdata: bytes) -> str:
    """Return readable preview of a text chunk's content."""
    try:
        if ctype == 'tEXt':
            return cdata.decode('latin-1', errors='replace')[:120]
        elif ctype == 'zTXt':
            null = cdata.index(b'\x00')
            key = cdata[:null].decode('latin-1', errors='replace')
            text = zlib.decompress(cdata[null+2:]).decode('utf-8', errors='replace')[:80]
            return f"{key}: {text}"
        elif ctype == 'iTXt':
            key, text = _decode_itxt(cdata)
            # Extract TC260 AIGC JSON if present
            if 'TC260' in text or 'tc260' in text:
                m = re.search(r'TC260:AIGC[^>]*>(\{[^<]+\})', text)
                if m:
                    try:
                        obj = json.loads(m.group(1).replace('&quot;', '"'))
                        return f"TC260/即梦国标: {json.dumps(obj, ensure_ascii=False)}"
                    except Exception:
                        pass
            return f"{key}: {text[:100]}"
        elif ctype == 'eXIf':
            return _decode_exif_json(cdata)
    except Exception:
        pass
    return cdata[:60].hex()


def clean_png(data: bytes) -> tuple[bytes, list[dict]]:
    """Strip all non-standard chunks. Returns (clean_bytes, removed_list)."""
    chunks = _read_png_chunks(data)
    removed = []
    out = bytearray(b'\x89PNG\r\n\x1a\n')

    for ctype, length, cdata in chunks:
        if ctype in KEEP_PNG_CHUNKS:
            # Reconstruct chunk with original CRC
            crc = struct.pack('>I', zlib.crc32(ctype.encode() + cdata) & 0xFFFFFFFF)
            out += struct.pack('>I', length)
            out += ctype.encode()
            out += cdata
            out += crc
        else:
            info = {'chunk': ctype, 'size': length}
            if ctype in ('tEXt', 'zTXt', 'iTXt'):
                info['content'] = _chunk_text_preview(ctype, cdata)
            removed.append(info)

    return bytes(out), removed


def check_png(data: bytes) -> list[dict]:
    """Report AI-related identifiers without modifying."""
    chunks = _read_png_chunks(data)
    found = []
    for ctype, length, cdata in chunks:
        if ctype not in KEEP_PNG_CHUNKS:
            info = {'chunk': ctype, 'size': length, 'type': 'non-standard'}
            if ctype in ('tEXt', 'zTXt', 'iTXt'):
                info['content'] = _chunk_text_preview(ctype, cdata)
                info['type'] = 'TC260国标' if (b'TC260' in cdata or b'tc260' in cdata) else 'text metadata'
            elif ctype == 'caBX':
                info['type'] = 'C2PA / JUMBF'
            elif ctype == 'eXIf':
                info['type'] = 'EXIF (嵌入式)'
                info['content'] = _decode_exif_json(cdata)
            found.append(info)
        elif ctype in ('tEXt', 'zTXt', 'iTXt'):
            # Standard text chunks — check for AI keywords
            for kw in AI_KEYWORDS:
                if kw in cdata:
                    found.append({
                        'chunk': ctype, 'size': length,
                        'type': 'AI metadata (text chunk)',
                        'content': _chunk_text_preview(ctype, cdata),
                    })
                    break
    return found


def clean_jpeg(input_path: str, output_path: str) -> list[dict]:
    """Re-save JPEG via Pillow — strips all EXIF/XMP/IPTC/C2PA."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow not installed. Run: pip install Pillow")

    img = Image.open(input_path)
    # Check what metadata existed
    removed = []
    if hasattr(img, '_getexif') and img._getexif():
        removed.append({'type': 'EXIF', 'content': 'prompt/seed/software tags'})
    if 'xmp' in (img.info or {}):
        removed.append({'type': 'XMP', 'content': 'DigitalSourceType and other XMP fields'})
    if img.info:
        for k in img.info:
            if any(kw.lower() in k.lower() for kw in ['c2pa', 'jfif', 'adobe', 'iptc']):
                removed.append({'type': k, 'content': str(img.info[k])[:80]})

    clean = Image.new(img.mode, img.size)
    clean.paste(img)
    clean.save(output_path, format='JPEG', quality=95, optimize=True)
    if not removed:
        removed.append({'type': 'EXIF/XMP/IPTC/C2PA', 'content': '(all metadata stripped via re-save)'})
    return removed


def remove_invisible_watermark(input_path: str, output_path: str) -> bool:
    """
    Attempt invisible watermark removal via noai-watermark (pip install noai-watermark).
    Requires ~4GB model storage and 8GB RAM. Returns True if successful.
    """
    try:
        from watermark_remover import remove_watermark
        from pathlib import Path
        remove_watermark(
            image_path=Path(input_path),
            output_path=Path(output_path),
            strength=0.04,
        )
        return True
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(description='Remove AI identifiers from images')
    parser.add_argument('input', help='Input image path (.png / .jpg / .jpeg)')
    parser.add_argument('output', nargs='?', help='Output path (default: <name>-clean.<ext>)')
    parser.add_argument('--check', action='store_true', help='Report AI identifiers only, no changes')
    parser.add_argument('--deep', action='store_true',
                        help='Also attempt invisible watermark removal (requires noai-watermark)')
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg'):
        print(f"Error: unsupported format {ext}. Use .png / .jpg / .jpeg")
        sys.exit(1)

    # --check mode
    if args.check:
        if ext == '.png':
            with open(input_path, 'rb') as f:
                data = f.read()
            found = check_png(data)
            if found:
                print(f"Found {len(found)} AI identifier(s) in {input_path}:")
                for item in found:
                    print(f"  [{item['chunk']}] {item['size']:,}b  {item.get('type','')}  {item.get('content','')[:80]}")
            else:
                print("No AI identifiers found.")
        else:
            print("JPEG check: open with exiftool or run without --check to strip metadata.")
        return

    # Determine output path
    output_path = args.output
    if not output_path:
        base, e = os.path.splitext(input_path)
        output_path = f"{base}-clean{e}"

    orig_size = os.path.getsize(input_path)

    # Step 1: scan first, show what will be removed
    if ext == '.png':
        with open(input_path, 'rb') as f:
            data = f.read()
        found = check_png(data)
        if found:
            print(f"Scan: found {len(found)} AI identifier(s):")
            for item in found:
                print(f"  [{item['chunk']}] {item['size']:,}b  {item.get('type','')}  {item.get('content','')[:80]}")
        else:
            print("Scan: no AI identifiers found.")
        print()

    # Step 2: strip metadata
    if ext == '.png':
        clean_data, removed = clean_png(data)
        with open(output_path, 'wb') as f:
            f.write(clean_data)
    else:
        removed = clean_jpeg(input_path, output_path)

    new_size = os.path.getsize(output_path)

    print(f"Input:   {input_path}  ({orig_size:,} bytes)")
    print(f"Output:  {output_path}  ({new_size:,} bytes)")
    print(f"Removed: {orig_size - new_size:,} bytes of metadata")
    if removed:
        for r in removed:
            label = r.get('chunk') or r.get('type', '?')
            size  = f"{r['size']:,}b" if 'size' in r else ''
            preview = r.get('content', '')[:80]
            print(f"  - [{label}] {size}  {preview}")
    else:
        print("  (no non-standard metadata found)")

    # --deep: invisible watermark removal
    if args.deep:
        print()
        print("Attempting invisible watermark removal (noai-watermark)...")
        deep_out = output_path.replace('-clean.', '-deep-clean.')
        ok = remove_invisible_watermark(output_path, deep_out)
        if ok:
            print(f"Deep clean saved to: {deep_out}")
            print("Targets: SynthID, StableSignature, TreeRing")
        else:
            print("noai-watermark not installed. Run:")
            print("  pip install noai-watermark")
            print("Then re-run with --deep")


if __name__ == '__main__':
    main()
