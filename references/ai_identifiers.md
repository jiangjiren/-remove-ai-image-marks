# AI Image Identifiers — Complete Reference

## Table of Contents
1. [Metadata-level identifiers](#1-metadata-level-removable-offline)
2. [Invisible pixel watermarks](#2-invisible-pixel-watermarks-require-diffusion-model)
3. [Visible watermarks](#3-visible-watermarks)
4. [Platform matrix](#4-platform-matrix)
5. [Open source removal tools](#5-open-source-removal-tools)

---

## 1. Metadata-level (removable offline)

### C2PA Content Credentials
- **PNG chunk**: `caBX` — JUMBF (JPEG Universal Metadata Box Format) container
- **JPEG marker**: `APP11` segment
- Contents: manifest URI, assertions, icon (SVG), cryptographic hash
- Platforms: Google Gemini, DALL-E 3, Adobe Firefly, Stable Diffusion (some builds)
- **Removal**: drop the chunk at binary level (our script handles this)

### PNG Text Chunks
Chunks `tEXt`, `zTXt`, `iTXt` — all carry AI generation metadata:

| Tool | Chunk key | Content |
|------|-----------|---------|
| Stable Diffusion A1111 | `parameters` | prompt, negative prompt, seed, model hash, CFG scale |
| ComfyUI | `workflow` | full JSON workflow graph |
| ComfyUI | `prompt` | JSON prompt execution data |
| InvokeAI | `invokeai_metadata` | JSON with model, seed, steps |
| InvokeAI | `invokeai_graph` | JSON workflow |
| Midjourney (older) | `Description` | job ID, prompt snippet |

**Removal**: drop all non-standard chunks (our script handles this)

### XMP Metadata
- Field: `dc:source`, `xmpRights:UsageTerms`, **`Iptc4xmpExt:DigitalSourceType`**
- Standard value for AI: `http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`
- Also in `photoshop:Source`, `xmp:CreatorTool`
- **Removal**: Pillow re-save strips all XMP (our script handles JPEG; PNG strips via chunk removal)

### EXIF Tags
Common AI-related EXIF fields:
- `Software`: model name (e.g. "Stable Diffusion 2.1", "DALL-E 3")
- `ImageDescription`: prompt text
- `UserComment`: generation parameters
- `Make` / `Model`: sometimes set to AI tool name
- **Removal**: Pillow re-save strips all EXIF

### TC260 国标（中国 AI 内容标注规范）
- **平台**：即梦 Dreamina（字节跳动）、国内遵守 GB/T 42905 的 AI 工具
- **载体**：PNG `iTXt` chunk，key 为 `XML:com.adobe.xmp`
- **内容**：`xmlns:TC260="http://www.tc260.org.cn/ns/AIGC/1.0/"` + `TC260:AIGC` JSON 字段
- **附带**：`eXIf` chunk（×2），EXIF UserComment 里有 `{"aigc_info":{"source_info":"dreamina"}}`
- **移除**：`iTXt` 和 `eXIf` 均不在标准白名单，脚本直接清除

### IPTC
- `IPTC:Caption-Abstract`: prompt
- `IPTC:Keywords`: "AI generated", "synthetic media"
- **Removal**: Pillow re-save strips IPTC

---

## 2. Invisible Pixel Watermarks (require diffusion model)

These are embedded **in the pixel values themselves** — metadata stripping cannot remove them.

### SynthID (Google DeepMind)
- **Platforms**: Google Gemini, Imagen, and licensed partners (100B+ images as of 2024)
- **Technique**: modifies pixel values in frequency domain; survives JPEG compression, resizing, cropping, color adjustments
- **Detection**: only Google can verify (proprietary model)
- **Removal approach**: VAE encode → add controlled noise (strength ~0.04) → denoise → decode
- **Tool**: `pip install noai-watermark` then `noai-watermark image.png -o clean.png`

### StableSignature (Meta)
- **Platforms**: Stable Diffusion (fine-tuned VAE decoder variant)
- **Technique**: 48-bit signature baked into VAE decoder weights; every image it generates carries the mark
- **Removal approach**: same diffusion regeneration as SynthID
- **Tool**: `noai-watermark` handles this

### TreeRing
- **Platforms**: research / some SD variants
- **Technique**: circular ring patterns injected into initial noise in Fourier space; survives many transformations
- **Removal approach**: diffusion regeneration disrupts the ring pattern
- **Tool**: `noai-watermark` handles this

### DWT Steganography (Stable Diffusion default)
- **Platforms**: Stability AI default SD builds (older versions)
- **Technique**: Discrete Wavelet Transform — hides 48-bit payload in wavelet coefficients
- **Removal approach**: lightweight — adding small noise (±1 LSB) or JPEG compression at 95%+ often suffices
- **Tool**: `remove-ai-watermarks invisible image.png`

---

## 3. Visible Watermarks

### Gemini Sparkle Logo
- **Platforms**: Google Gemini (image generation outputs, especially mobile/web UI)
- **Technique**: alpha-blended sparkle icon overlay at a corner of the image
- **Removal approach**: reverse alpha blending: `original = (watermarked - α × logo) / (1 - α)`
  Uses NCC (Normalized Cross-Correlation) to locate the logo dynamically
- **Tool**: `remove-ai-watermarks visible image.png`

---

## 4. Platform Matrix

| Platform | C2PA | PNG text | XMP | EXIF | Invisible WM | Visible WM |
|----------|------|----------|-----|------|-------------|------------|
| Google Gemini | YES | — | YES | YES | SynthID | Sparkle logo |
| DALL-E 3 | YES | — | YES | — | — | — |
| Adobe Firefly | YES | — | YES | — | — | — |
| Stable Diffusion A1111 | — | `parameters` | — | Software tag | DWT (older) | — |
| ComfyUI | — | `workflow`/`prompt` | — | — | — | — |
| InvokeAI | — | `invokeai_*` | — | — | — | — |
| Midjourney | — | Sometimes | Sometimes | Sometimes | — | — |
| Meta Imagine | — | — | YES | — | StableSignature | — |
| 即梦 Dreamina (字节) | — | — | TC260 XMP | eXIf JSON | — | — |

---

## 5. Open Source Removal Tools

### noai-watermark (recommended for invisible WM)
- **Repo**: github.com/mertizci/noai-watermark
- **Install**: `pip install noai-watermark`
- **Targets**: SynthID, StableSignature, TreeRing + metadata
- **Mechanism**: VAE latent encode → noise injection → diffusion denoise
- **Requirements**: Python 3.10+, ~4GB model storage, 8GB RAM (GPU optional)
```bash
noai-watermark image.png -o clean.png                    # default (strength=0.04)
noai-watermark image.png --strength 0.15 --steps 60 -o clean.png  # stronger
noai-watermark image.png --model-profile ctrlregen -o clean.png   # best quality
```

### remove-ai-watermarks (broadest platform support)
- **Repo**: github.com/wiltodelta/remove-ai-watermarks
- **Install**: `pipx install git+https://github.com/wiltodelta/remove-ai-watermarks.git`
- **Targets**: Gemini visible logo, SynthID, DWT, C2PA, EXIF/XMP, PNG chunks
- **Requirements**: Python 3.10+, GPU recommended for invisible WM
```bash
remove-ai-watermarks all image.png -o clean.png          # full pipeline
remove-ai-watermarks visible image.png -o clean.png      # visible only (fast, offline)
remove-ai-watermarks invisible image.png -o clean.png    # pixel-level (needs GPU)
remove-ai-watermarks metadata image.png --remove         # metadata only
```

### Our bundled script (clean_image.py)
- **No external deps beyond Pillow** — fast, offline
- Handles: C2PA, all PNG text chunks, EXIF, XMP, IPTC
- Does NOT handle invisible watermarks
- Use `--check` to scan without modifying
- Use `--deep` to chain with `noai-watermark` if installed
