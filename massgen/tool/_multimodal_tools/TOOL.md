---
name: multimodal-tools
description: Understand images/screenshots/charts, transcribe audio/video, analyze PDFs with AI vision
category: multimodal
requires_api_keys: [OPENAI_API_KEY]
tasks:
  - "Analyze and understand images with vision models"
  - "Understand and transcribe audio files"
  - "Analyze video content frame-by-frame"
  - "Process and understand various file formats (PDF, DOCX, etc.)"
  - "Generate images from text descriptions"
  - "Generate videos from text prompts"
  - "Convert text to speech with natural voices"
  - "Transform images to new variations"
keywords: [vision, audio, video, multimodal, image-analysis, speech, transcription, generation, pdf, file-processing]
---

# Multimodal Tools

Comprehensive suite of tools for processing and understanding vision, audio, video, and file content using OpenAI's multimodal APIs.

## Purpose

Enable agents to work with media beyond text:
- **Vision**: Analyze images, screenshots, charts, diagrams
- **Audio**: Transcribe speech, understand audio content
- **Video**: Process and analyze video frames
- **File Processing**: Extract content from PDFs, documents, etc.
- **Generation**: Create images, videos, and speech from text

## When to Use This Tool

**Use multimodal tools when:**
- Analyzing screenshots, charts, or visual data
- Extracting information from images or videos
- Transcribing audio recordings or understanding speech
- Processing document files (PDF, DOCX, XLSX)
- Generating visual or audio content
- Working with multi-format media files

**Do NOT use for:**
- Simple text processing (use text tools instead)
- Real-time video streaming analysis
- High-volume batch processing (consider costs)
- Tasks not requiring multimodal understanding

## Available Functions

### Understanding Tools

#### `understand_image(image_path: str, prompt: str, ...) -> ExecutionResult`
Analyze images using vision models (GPT-4.1 or similar).

**Example:**
```python
result = await understand_image(
    "screenshot.png",
    "What buttons are visible in this UI?"
)
# Returns: Detailed description of UI elements
```

**Use cases:**
- Screenshot analysis
- Chart/graph interpretation
- Visual content extraction
- UI testing verification

#### `understand_audio(audio_path: str, prompt: str, ...) -> ExecutionResult`
Transcribe and understand audio files.

**Example:**
```python
result = await understand_audio(
    "recording.mp3",
    "Transcribe this audio and summarize key points"
)
# Returns: Transcription and summary
```

**Supported formats:** MP3, WAV, M4A, etc.

#### `understand_video(video_path: str, prompt: str, ...) -> ExecutionResult`
Analyze video content by processing frames.

**Example:**
```python
result = await understand_video(
    "demo.mp4",
    "Describe what happens in this video"
)
# Returns: Frame-by-frame analysis
```

**Note:** Processes video by extracting and analyzing key frames.

#### `understand_file(file_path: str, prompt: str, ...) -> ExecutionResult`
Extract and understand content from various file formats.

**Example:**
```python
result = await understand_file(
    "report.pdf",
    "Summarize the main findings"
)
# Returns: Extracted content and analysis
```

**Supported formats:** PDF, DOCX, XLSX, TXT, CSV, etc.

### Generation Tools

#### `text_to_image_generation(prompt: str, output_path: str, ...) -> ExecutionResult`
Generate images from text descriptions.

**Example:**
```python
result = await text_to_image_generation(
    "A serene mountain landscape at sunset",
    "landscape.png"
)
# Saves: landscape.png
```

**Model:** DALL-E or similar image generation models.

#### `image_to_image_generation(image_path: str, prompt: str, output_path: str, ...) -> ExecutionResult`
Transform existing images based on prompts.

**Example:**
```python
result = await image_to_image_generation(
    "photo.jpg",
    "Make it look like a watercolor painting",
    "watercolor.png"
)
# Saves: watercolor.png
```

#### `text_to_video_generation(prompt: str, output_path: str, ...) -> ExecutionResult`
Generate videos from text descriptions.

**Example:**
```python
result = await text_to_video_generation(
    "A cat playing with yarn",
    "cat_video.mp4"
)
# Saves: cat_video.mp4
```

**Note:** Video generation may take significant time and credits.

#### `text_to_speech_transcription_generation(text: str, output_path: str, ...) -> ExecutionResult`
Convert text to natural speech.

**Example:**
```python
result = await text_to_speech_transcription_generation(
    "Hello, this is a test of the speech synthesis system.",
    "speech.mp3"
)
# Saves: speech.mp3
```

**Features:** Multiple voices, adjustable speed, natural prosody.

#### `text_to_speech_continue_generation(text: str, previous_audio: str, output_path: str, ...) -> ExecutionResult`
Continue speech generation with context from previous audio.

**Example:**
```python
result = await text_to_speech_continue_generation(
    "And here's the next sentence.",
    "speech.mp3",
    "speech_continued.mp3"
)
# Saves: speech_continued.mp3 with matching voice/style
```

#### `text_to_file_generation(content: str, output_path: str, file_format: str, ...) -> ExecutionResult`
Generate structured files from text (PDF, DOCX, etc.).

**Example:**
```python
result = await text_to_file_generation(
    "# Report\n\nThis is the content...",
    "report.pdf",
    "pdf"
)
# Saves: report.pdf
```

**Supported formats:** PDF, DOCX, TXT, MD, HTML.

## Configuration

### Prerequisites

**Environment variables:**
```bash
export OPENAI_API_KEY="your-api-key"
```

**Optional dependencies:**
```bash
pip install pillow  # For image processing
pip install ffmpeg-python  # For video processing
```

### YAML Config

Enable multimodal tools in your config:

```yaml
custom_tools_path: "massgen/tool/_multimodal_tools"
```

Or include specific tools in your tools list.

## Path Handling

All tools support flexible path handling:
- **Relative paths**: Resolved relative to agent workspace
- **Absolute paths**: Must be within allowed directories
- **Output paths**: Saved to workspace by default

**Validation:** Path access is validated for security.

## Cost Considerations

**Be mindful of API costs:**
- Image analysis: ~$0.01-0.05 per image
- Video analysis: Cost scales with duration/frames
- Image generation: ~$0.02-0.08 per image
- Video generation: Significantly higher costs
- Audio transcription: ~$0.006 per minute

Always consider cost when processing large batches.

## Limitations

- **API dependencies**: Requires OpenAI API access and credits
- **File size limits**: Large files may exceed API limits
- **Processing time**: Video/audio processing can be slow
- **Quality variability**: Generated content quality depends on prompts
- **Format support**: Not all file formats supported for all operations
- **Network required**: All operations require internet access

## Common Use Cases

1. **Screenshot analysis**: Understand UI elements, extract text from images
2. **Document processing**: Extract information from PDFs, reports
3. **Media transcription**: Convert audio/video to text
4. **Visual content creation**: Generate images for presentations, reports
5. **Accessibility**: Convert text to speech, extract text from images
6. **Video analysis**: Understand video content without watching
7. **Chart/graph interpretation**: Extract data from visual charts
