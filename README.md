# remove-ai-image-marks

**English** | [中文](#中文说明)

A Claude Code skill that automatically scans and removes all AI-generated image identifiers from PNG/JPEG files — including C2PA content credentials, TC260 Chinese national AIGC standard labels, EXIF/XMP metadata, and PNG text chunks.

---

## Features

- **Auto-scan before cleaning** — shows exactly what was found before removing anything
- **Binary-level PNG stripping** — drops non-standard chunks directly, zero pixel change
- **JPEG support** — re-saves via Pillow to strip all EXIF/XMP/IPTC/C2PA
- **TC260 aware** — recognizes China's national AIGC labeling standard (GB/T 42905), used by 即梦 (Dreamina), 可灵, and other Chinese AI tools
- **Deep clean mode** — optional invisible watermark removal (SynthID, StableSignature, TreeRing) via `noai-watermark`
- **No GPU required** for standard metadata cleaning

## What Gets Removed

| Identifier | Format | Platforms |
|-----------|--------|-----------|
| C2PA Content Credentials (`caBX`) | PNG / JPEG | Google Gemini, DALL-E 3, GPT Image 1, Adobe Firefly |
| TC260 AIGC label (`iTXt` XMP) | PNG | 即梦 Dreamina, 可灵, other CN tools |
| EXIF trace JSON (`eXIf`) | PNG | 即梦 Dreamina (ContentProducer ID, trace ID) |
| SD generation params (`tEXt`) | PNG | Stable Diffusion A1111 |
| Workflow JSON (`iTXt`) | PNG | ComfyUI, InvokeAI |
| XMP `DigitalSourceType` | JPEG | Multi-platform standard |
| EXIF prompt/seed/software | JPEG | Midjourney, Stable Diffusion |
| SynthID (pixel-level) | PNG / JPEG | Google Gemini / Imagen (requires `--deep`) |
| StableSignature (pixel-level) | PNG / JPEG | Meta / SD variants (requires `--deep`) |

## Requirements

- Python 3.10+
- Pillow (`pip install Pillow`)
- Claude Code with skills support

## Installation

Clone into your Claude Code skills directory:

```bash
# macOS / Linux
git clone https://github.com/jiangjiren/-remove-ai-image-marks.git ~/.claude/skills/remove-ai-image-marks

# Windows
git clone https://github.com/jiangjiren/-remove-ai-image-marks.git %USERPROFILE%\.claude\skills\remove-ai-image-marks
```

Restart Claude Code — the skill appears automatically.

## Usage

Just describe what you want in natural language:

> "帮我去掉这张图片的AI标识"
> "remove AI watermarks from this image"
> "清除图片的C2PA内容凭证"

Claude will invoke the skill and run the script automatically.

You can also run the script directly:

```bash
# Scan only (no changes)
python scripts/clean_image.py image.png --check

# Clean metadata (default output: image-clean.png)
python scripts/clean_image.py image.png

# Custom output path
python scripts/clean_image.py image.png output.png

# Deep clean: also remove invisible watermarks (requires noai-watermark)
pip install noai-watermark
python scripts/clean_image.py image.png --deep
```

## Example Output

```
Scan: found 3 AI identifier(s):
  [iTXt] 723b  TC260国标  TC260/即梦国标: {"Label":"1","ContentProducer":"001191...","ProduceID":"tos-cn-i-..."}
  [eXIf] 251b  EXIF (嵌入式)  {"aigc_info":{"source_info":"dreamina"},"trace_info":{"originItemId":"762710..."}}
  [eXIf] 251b  EXIF (嵌入式)  {"aigc_info":{"source_info":"dreamina"},...}

Input:   image.png  (3,536,224 bytes)
Output:  image-clean.png  (3,534,963 bytes)
Removed: 1,261 bytes of metadata
  - [iTXt] 723b
  - [eXIf] 251b
  - [eXIf] 251b
```

## Invisible Watermark Removal (Optional)

For pixel-level watermarks like SynthID (Google Gemini) that survive metadata stripping:

```bash
pip install noai-watermark   # ~4GB model download on first run, 8GB RAM required
python scripts/clean_image.py image.png --deep
```

This uses a diffusion model to re-generate the image with controlled noise, disrupting the embedded signal while preserving visual quality.

> **Note:** Invisible watermarks embedded in pixel data (SynthID, StableSignature, TreeRing) cannot be removed by metadata stripping alone. Standard metadata cleaning handles the vast majority of real-world cases.

---

## 中文说明

一个 Claude Code 技能，自动扫描并清除 PNG/JPEG 图片中的所有 AI 生成标识，包括 C2PA 内容凭证、TC260 国家标准 AIGC 标签、EXIF/XMP 元数据，以及 PNG 文本块。

### 功能特点

- **清除前自动扫描** — 先显示发现了什么，再执行清除
- **PNG 二进制层操作** — 直接丢弃非标准 chunk，像素完全不变
- **支持 JPEG** — 通过 Pillow 重新保存，剥离全部 EXIF/XMP/IPTC/C2PA
- **识别 TC260 国标** — 支持中国国家 AIGC 内容标注标准（GB/T 42905），覆盖即梦、可灵等国内 AI 工具
- **深度清理模式** — 可选隐形水印移除（SynthID、StableSignature、TreeRing）
- **离线运行** — 标准元数据清理无需 GPU、无需联网

### 支持的 AI 平台

| 平台 | 标识类型 | 是否覆盖 |
|------|---------|---------|
| Google Gemini | C2PA + SynthID 隐形水印 | 元数据 ✅ / 隐形水印需 `--deep` |
| DALL-E 3 / GPT Image 1 | C2PA | ✅ |
| Adobe Firefly | C2PA + XMP | ✅ |
| 即梦 Dreamina | TC260 国标 XMP + eXIf 追踪 ID | ✅ |
| Stable Diffusion A1111 | PNG tEXt 提示词参数 | ✅ |
| ComfyUI | PNG iTXt 工作流 JSON | ✅ |
| InvokeAI | PNG iTXt 生成参数 | ✅ |
| Midjourney | EXIF/XMP | ✅ |
| Meta Imagine | StableSignature 隐形水印 | 需 `--deep` |

### 安装

```bash
# macOS / Linux
git clone https://github.com/jiangjiren/-remove-ai-image-marks.git ~/.claude/skills/remove-ai-image-marks

# Windows
git clone https://github.com/jiangjiren/-remove-ai-image-marks.git %USERPROFILE%\.claude\skills\remove-ai-image-marks
```

重启 Claude Code，技能自动生效。

### 使用方式

直接用自然语言描述需求，Claude 会自动调用技能：

> "帮我去掉这张图片的AI标识"
> "清除图片的C2PA内容凭证"
> "remove AI watermarks from this image"

也可以直接运行脚本：

```bash
# 仅扫描，不修改
python scripts/clean_image.py image.png --check

# 清除元数据（输出 image-clean.png）
python scripts/clean_image.py image.png

# 指定输出路径
python scripts/clean_image.py image.png output.png

# 深度清理（同时去除像素级隐形水印）
pip install noai-watermark
python scripts/clean_image.py image.png --deep
```

### TC260 国标说明

即梦（Dreamina）等国内 AI 工具遵守 GB/T 42905 标准，在图片中嵌入以下追踪信息：

- `ContentProducer` — 字节跳动在政府 TC260 系统的备案注册号
- `ProduceID` — 图片在字节 TOS 云存储上的唯一 ID（可溯源到原始生成请求）
- `originItemId` — 生成请求追踪 ID
- `source_info: "dreamina"` — 来源标识

本技能会识别并清除上述全部字段。

### 隐形水印说明

SynthID（Google）等隐形水印嵌入在**像素值本身**中，无法通过元数据剥离去除。如需处理，使用 `--deep` 模式，脚本会调用扩散模型对图片进行重生成（需要 `pip install noai-watermark`，首次运行下载约 4GB 模型，需要 8GB 内存）。

---

## License

MIT
