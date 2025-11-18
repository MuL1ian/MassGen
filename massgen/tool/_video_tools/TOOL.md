---
name: video-tools
description: Video editing and caption generation using FFmpeg and Whisper
category: video-processing
requires_api_keys: []
tasks:
  - "Speed up or slow down video playback"
  - "Trim and cut video segments"
  - "Convert video formats"
  - "Generate captions and subtitles from video audio"
  - "Merge multiple video files"
  - "Extract audio from videos"
keywords: [video, ffmpeg, editing, captions, subtitles, whisper, video-processing, conversion, trimming]
---

# Video Tools

Video editing and caption generation tools using FFmpeg and Whisper for common video processing tasks.

## Purpose

Enable agents to:
- Edit videos (speed, trim, convert formats)
- Generate captions/subtitles automatically
- Process video files for analysis or presentation
- Extract and manipulate video content
- Create accessible video content with captions

## When to Use This Tool

**Use video tools when:**
- Need to edit video speed, duration, or format
- Generating captions/subtitles from video audio
- Trimming or cutting video segments
- Converting between video formats
- Extracting audio from video
- Merging video files

**Do NOT use for:**
- Complex video effects (use professional video editors)
- Real-time video processing
- Live streaming
- 3D video editing
- Advanced color grading

## Available Functions

### Video Editing

#### `speed_up_video(input_path: str, output_path: str, speed_factor: float, ...) -> ExecutionResult`

Change video playback speed.

**Example - Speed up 2x:**
```python
result = await speed_up_video(
    "input.mp4",
    "output_2x.mp4",
    speed_factor=2.0
)
# Creates: Video playing 2x faster
```

**Example - Slow down 0.5x:**
```python
result = await speed_up_video(
    "input.mp4",
    "output_slow.mp4",
    speed_factor=0.5
)
# Creates: Video playing at half speed
```

**Parameters:**
- `input_path` (str): Input video file
- `output_path` (str): Output video file
- `speed_factor` (float): Speed multiplier (>1 = faster, <1 = slower)
- `allowed_paths` (List[str], optional): Allowed directories for validation

**Speed factor examples:**
- `0.25` = Quarter speed (slow motion)
- `0.5` = Half speed
- `2.0` = Double speed
- `4.0` = 4x speed (time-lapse)

#### `trim_video(input_path: str, output_path: str, start_time: str, duration: str, ...) -> ExecutionResult`

Extract a segment from video.

**Example:**
```python
result = await trim_video(
    "long_video.mp4",
    "clip.mp4",
    start_time="00:02:30",  # Start at 2min 30sec
    duration="00:01:00"      # Duration 1 minute
)
# Creates: 1-minute clip starting at 2:30
```

**Time format:** `HH:MM:SS` or `MM:SS` or `SS`

**Parameters:**
- `input_path` (str): Input video file
- `output_path` (str): Output video file
- `start_time` (str): When to start clip (HH:MM:SS)
- `duration` (str): How long the clip should be

#### `convert_video_format(input_path: str, output_path: str, format: str, ...) -> ExecutionResult`

Convert video to different format.

**Example:**
```python
result = await convert_video_format(
    "input.mov",
    "output.mp4",
    format="mp4"
)
# Converts: MOV to MP4
```

**Supported formats:** MP4, AVI, MOV, MKV, WEBM, etc.

#### `merge_videos(input_paths: List[str], output_path: str, ...) -> ExecutionResult`

Concatenate multiple videos.

**Example:**
```python
result = await merge_videos(
    ["clip1.mp4", "clip2.mp4", "clip3.mp4"],
    "combined.mp4"
)
# Creates: Single video with all clips
```

**Note:** Videos should have same resolution/codec for best results.

#### `extract_audio(input_path: str, output_path: str, ...) -> ExecutionResult`

Extract audio track from video.

**Example:**
```python
result = await extract_audio(
    "video.mp4",
    "audio.mp3"
)
# Creates: MP3 audio file
```

**Supported formats:** MP3, WAV, AAC, FLAC, etc.

### Caption Generation

#### `generate_captions(video_path: str, output_path: str, language: str = 'en', ...) -> ExecutionResult`

Generate captions/subtitles from video audio using Whisper.

**Example:**
```python
result = await generate_captions(
    "lecture.mp4",
    "lecture.srt"
)
# Creates: SRT subtitle file
```

**Example with language:**
```python
result = await generate_captions(
    "french_video.mp4",
    "french_subs.srt",
    language="fr"
)
# Creates: French subtitles
```

**Parameters:**
- `video_path` (str): Input video file
- `output_path` (str): Output subtitle file (.srt, .vtt)
- `language` (str): Language code (default: 'en')
  - 'en' = English
  - 'es' = Spanish
  - 'fr' = French
  - 'de' = German
  - 'ja' = Japanese
  - etc.
- `model` (str): Whisper model size (tiny/base/small/medium/large)

**Whisper models:**
- `tiny`: Fastest, least accurate
- `base`: Fast, reasonable accuracy
- `small`: Good balance (default)
- `medium`: Better accuracy, slower
- `large`: Best accuracy, slowest

## Configuration

### Prerequisites

**Install FFmpeg:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt-get install ffmpeg

# Windows
choco install ffmpeg
```

**Install Whisper (for captions):**
```bash
pip install openai-whisper
```

**Verify installations:**
```bash
ffmpeg -version
python -c "import whisper; print(whisper.__version__)"
```

### YAML Config

Enable video tools in your config:

```yaml
custom_tools_path: "massgen/tool/_video_tools"

# Or add specific tools
tools:
  - name: speed_up_video
  - name: generate_captions
```

## Path Handling

**Relative paths:**
- Resolved relative to agent workspace
- Example: `"videos/input.mp4"` → `{workspace}/videos/input.mp4`

**Absolute paths:**
- Must be within allowed directories (if validation enabled)

**Output paths:**
- Automatically created in workspace
- Parent directories created if needed

## Processing Time

Video processing can take time depending on:

**Speed factors:**
- Trim: Fast (re-encodes segment only)
- Format conversion: Medium (depends on formats)
- Speed change: Medium (re-encodes with new timing)
- Merge: Fast if same format, medium if re-encoding
- Captions: Slow (Whisper transcription takes time)

**Typical times:**
- 5-min video trim: 10-30 seconds
- 5-min video speed change: 1-2 minutes
- 5-min caption generation: 2-5 minutes (depending on model)

## Caption Formats

**SRT (SubRip):**
```
1
00:00:00,000 --> 00:00:05,000
This is the first subtitle.

2
00:00:05,000 --> 00:00:10,000
This is the second subtitle.
```

**VTT (WebVTT):**
```
WEBVTT

00:00:00.000 --> 00:00:05.000
This is the first subtitle.

00:00:05.000 --> 00:00:10.000
This is the second subtitle.
```

Both formats widely supported by video players.

## Common Use Cases

### 1. Create Time-Lapse

```python
# Speed up 10x for time-lapse effect
await speed_up_video("construction.mp4", "timelapse.mp4", speed_factor=10.0)
```

### 2. Make Highlight Reel

```python
# Extract exciting moment
await trim_video("game.mp4", "highlight.mp4", "00:15:30", "00:00:45")
```

### 3. Add Subtitles

```python
# Generate captions
await generate_captions("interview.mp4", "interview.srt")
# Use captions in video player or burn into video
```

### 4. Convert for Web

```python
# Convert to web-friendly format
await convert_video_format("original.avi", "web.mp4", "mp4")
```

### 5. Extract Podcast Audio

```python
# Get audio from video podcast
await extract_audio("podcast_video.mp4", "podcast.mp3")
```

### 6. Combine Clips

```python
# Merge presentation segments
clips = ["intro.mp4", "main.mp4", "outro.mp4"]
await merge_videos(clips, "full_presentation.mp4")
```

## Limitations

- **FFmpeg required**: Must have FFmpeg installed
- **Whisper for captions**: Requires openai-whisper package
- **Processing time**: Large videos take time to process
- **Disk space**: Processing creates temporary files
- **Format compatibility**: Some formats may not support all operations
- **Quality loss**: Re-encoding may reduce quality (use high bitrates)
- **No GPU acceleration**: Uses CPU by default (can be slow)
- **Caption accuracy**: Depends on audio quality and Whisper model

## Best Practices

**1. Choose appropriate Whisper model:**
```python
# Fast processing, good enough
await generate_captions(video, output, model="small")

# Best accuracy, slower
await generate_captions(video, output, model="large")
```

**2. Preserve quality when converting:**
```python
# Include quality settings if available
await convert_video_format(input, output, format="mp4", quality="high")
```

**3. Trim before processing:**
```python
# More efficient to trim first, then apply effects
await trim_video("long.mp4", "segment.mp4", "00:10:00", "00:05:00")
await speed_up_video("segment.mp4", "fast_segment.mp4", 2.0)
```

**4. Use consistent formats:**
```python
# Convert all to same format before merging
for video in videos:
    await convert_video_format(video, f"{video}_mp4", "mp4")
await merge_videos(converted_videos, "merged.mp4")
```

**5. Clean up intermediate files:**
```python
# Remove temporary files after processing
import os
os.remove("temp_video.mp4")
```

## Common Issues

**Issue: FFmpeg not found**
- Solution: Install FFmpeg and add to PATH

**Issue: Caption generation fails**
- Solution: Check audio quality, install Whisper, check language code

**Issue: Video quality degraded**
- Solution: Use higher bitrate settings or lossless formats

**Issue: Merge fails with "format mismatch"**
- Solution: Convert all videos to same format first

**Issue: Slow processing**
- Solution: Use smaller Whisper model, reduce video resolution, or trim first
