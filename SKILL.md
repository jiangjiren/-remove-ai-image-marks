---
name: remove-ai-image-marks
description: Remove C2PA content credentials and all hidden AI identifiers from PNG/JPEG images. Use when the user wants to remove C2PA, AI metadata (tEXt/XMP/EXIF/IPTC), or invisible watermarks (SynthID, StableSignature, TreeRing). Triggers on requests like "删除C2PA"、"清除图片元数据"、"去除AI标识"、"去掉AI水印"、"remove image metadata"、"remove AI watermark"、"strip content credentials"、"删除图片标识"、"去AI标记".
---

# Image Cleaner

Two-tier approach: fast offline metadata stripping (bundled script, no extra deps), plus optional invisible watermark removal via open-source diffusion tools.

For the complete list of AI identifier types and platform coverage, read `references/ai_identifiers.md`.

## Tier 1 — Metadata stripping (fast, offline, no GPU)

Handles: C2PA (`caBX`), PNG text chunks (`tEXt`/`zTXt`/`iTXt`), EXIF, XMP, IPTC.
Covers: Gemini, DALL-E 3, Firefly, Stable Diffusion (A1111/ComfyUI/InvokeAI), Midjourney.

```bash
# Check what AI identifiers are present (no changes made)
python C:\Users\lenovo\.claude\skills\image-cleaner\scripts\clean_image.py image.png --check

# Strip all metadata (default output: image-clean.png)
python C:\Users\lenovo\.claude\skills\image-cleaner\scripts\clean_image.py image.png

# Custom output path
python C:\Users\lenovo\.claude\skills\image-cleaner\scripts\clean_image.py image.png output.png
```

**PNG**: drops all non-standard chunks at binary level. Standard chunks kept:
`IHDR IDAT IEND PLTE tRNS cHRM gAMA iCCP sRGB bKGD hIST tIME pHYs sBIT sPLT`

**JPEG**: Pillow re-save with clean Image object — strips all EXIF/XMP/IPTC/C2PA.

## Tier 2 — Invisible watermark removal (requires install + GPU)

Targets: SynthID (Google), StableSignature (Meta), TreeRing, DWT steganography.
Mechanism: VAE encode → controlled noise injection → diffusion denoise → decode.

```bash
# Install noai-watermark (one-time, ~4GB models)
pip install noai-watermark

# Use --deep flag to chain both tiers
python C:\Users\lenovo\.claude\skills\image-cleaner\scripts\clean_image.py image.png --deep

# Or use noai-watermark directly for more control
noai-watermark image.png -o clean.png
noai-watermark image.png --strength 0.15 --steps 60 -o clean.png  # stronger removal
noai-watermark image.png --model-profile ctrlregen -o clean.png   # best quality
```

For Gemini sparkle logo or broader platform support, use `remove-ai-watermarks`:
```bash
pipx install git+https://github.com/wiltodelta/remove-ai-watermarks.git
remove-ai-watermarks all image.png -o clean.png
remove-ai-watermarks visible image.png -o clean.png   # visible logo only (fast)
```

## Workflow

1. Run `--check` first to report what's in the image.
2. Run Tier 1 (bundled script) — covers most cases, no extra setup.
3. If user asks about invisible watermarks (SynthID etc.), guide them to install `noai-watermark` and use `--deep`.
4. Report: original size, cleaned size, list of removed items with content preview.

## Decision guide

| Situation | Approach |
|-----------|----------|
| Gemini / DALL-E / Firefly image | Tier 1 covers C2PA + XMP |
| SD A1111 / ComfyUI image | Tier 1 covers PNG text chunks |
| Google Gemini + worried about SynthID | Tier 1 + Tier 2 (`--deep`) |
| Gemini sparkle logo visible | `remove-ai-watermarks visible` |
| Batch processing | `noai-watermark` Python API supports batch |
