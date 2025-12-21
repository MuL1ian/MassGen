# -*- coding: utf-8 -*-
"""
Tests for the read_media tool and multimodal injection functionality.

Tests:
- Media type detection from file extensions
- Model modality support checking
- Fallback to understand_* tools for non-MM models
- Native MM path with multimodal_inject metadata
- Path validation and error handling
"""

import base64
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from massgen.backend.capabilities import ModelModalities, model_supports_media_type
from massgen.tool._multimodal_tools.read_media import (
    _detect_media_type,
    _get_mime_type,
    _read_and_encode,
    _validate_path_access,
    read_media,
)


class TestMediaTypeDetection:
    """Test suite for media type detection from file extensions."""

    def test_detect_image_types(self):
        """Test detection of image file types."""
        image_files = [
            ("test.png", "image"),
            ("test.PNG", "image"),
            ("photo.jpg", "image"),
            ("photo.JPEG", "image"),
            ("animation.gif", "image"),
            ("modern.webp", "image"),
            ("bitmap.bmp", "image"),
        ]
        for filename, expected in image_files:
            result = _detect_media_type(filename)
            assert result == expected, f"Expected {expected} for {filename}, got {result}"

    def test_detect_audio_types(self):
        """Test detection of audio file types."""
        audio_files = [
            ("song.mp3", "audio"),
            ("recording.wav", "audio"),
            ("podcast.m4a", "audio"),
            ("music.ogg", "audio"),
            ("lossless.flac", "audio"),
            ("track.aac", "audio"),
        ]
        for filename, expected in audio_files:
            result = _detect_media_type(filename)
            assert result == expected, f"Expected {expected} for {filename}, got {result}"

    def test_detect_video_types(self):
        """Test detection of video file types."""
        video_files = [
            ("movie.mp4", "video"),
            ("clip.mov", "video"),
            ("old.avi", "video"),
            ("hd.mkv", "video"),
            ("web.webm", "video"),
        ]
        for filename, expected in video_files:
            result = _detect_media_type(filename)
            assert result == expected, f"Expected {expected} for {filename}, got {result}"

    def test_unsupported_types(self):
        """Test that unsupported file types return None."""
        unsupported_files = [
            "document.pdf",
            "script.py",
            "data.json",
            "archive.zip",
            "noextension",
            "",
        ]
        for filename in unsupported_files:
            result = _detect_media_type(filename)
            assert result is None, f"Expected None for {filename}, got {result}"


class TestMimeTypeDetection:
    """Test suite for MIME type detection."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_image_mime_types(self, temp_dir):
        """Test MIME type detection for images."""
        test_cases = [
            ("test.png", "image/png"),
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"),
            ("test.gif", "image/gif"),
            ("test.webp", "image/webp"),
            ("test.bmp", "image/bmp"),
        ]
        for filename, expected_mime in test_cases:
            path = temp_dir / filename
            result = _get_mime_type(path)
            assert result == expected_mime, f"Expected {expected_mime} for {filename}, got {result}"

    def test_audio_mime_types(self, temp_dir):
        """Test MIME type detection for audio."""
        test_cases = [
            ("test.mp3", "audio/mpeg"),
            ("test.wav", {"audio/wav", "audio/x-wav"}),  # Platform-specific
            ("test.ogg", "audio/ogg"),
            ("test.flac", {"audio/flac", "audio/x-flac"}),  # Platform-specific
        ]
        for filename, expected_mime in test_cases:
            path = temp_dir / filename
            result = _get_mime_type(path)
            if isinstance(expected_mime, set):
                assert result in expected_mime, f"Expected one of {expected_mime} for {filename}, got {result}"
            else:
                assert result == expected_mime, f"Expected {expected_mime} for {filename}, got {result}"


class TestModelModalitySupport:
    """Test suite for model modality checking."""

    def test_openai_model_image_support(self):
        """Test that OpenAI models report correct image support."""
        # These models should support images
        assert model_supports_media_type("openai", "gpt-4o", "image") is True
        assert model_supports_media_type("openai", "gpt-5.1-codex", "image") is True

    def test_openai_model_audio_support(self):
        """Test that OpenAI models report correct audio support."""
        # gpt-4o supports audio, gpt-4.1 does not
        assert model_supports_media_type("openai", "gpt-4o", "audio") is True
        assert model_supports_media_type("openai", "gpt-4.1", "audio") is False

    def test_claude_model_image_support(self):
        """Test that Claude models report correct image support."""
        assert model_supports_media_type("claude", "claude-sonnet-4-5", "image") is True
        assert model_supports_media_type("claude", "claude-opus-4-5", "image") is True

    def test_claude_model_audio_video_not_supported(self):
        """Test that Claude models don't support audio/video natively."""
        assert model_supports_media_type("claude", "claude-sonnet-4-5", "audio") is False
        assert model_supports_media_type("claude", "claude-sonnet-4-5", "video") is False

    def test_gemini_full_multimodal_support(self):
        """Test that Gemini models support all media types."""
        for model in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3-flash-preview"]:
            assert model_supports_media_type("gemini", model, "image") is True
            assert model_supports_media_type("gemini", model, "audio") is True
            assert model_supports_media_type("gemini", model, "video") is True

    def test_unknown_model_returns_false(self):
        """Test that unknown models return False."""
        assert model_supports_media_type("openai", "unknown-model", "image") is False
        assert model_supports_media_type("unknown-backend", "gpt-4o", "image") is False

    def test_unknown_media_type_returns_false(self):
        """Test that unknown media types return False."""
        assert model_supports_media_type("openai", "gpt-4o", "hologram") is False


class TestPathValidation:
    """Test suite for path validation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_path_within_allowed(self, temp_dir):
        """Test that paths within allowed directories pass validation."""
        file_path = temp_dir / "test.png"
        # Should not raise
        _validate_path_access(file_path, [temp_dir])

    def test_path_outside_allowed_raises(self, temp_dir):
        """Test that paths outside allowed directories raise ValueError."""
        other_dir = Path("/some/other/path")
        file_path = other_dir / "test.png"

        with pytest.raises(ValueError, match="not in allowed directories"):
            _validate_path_access(file_path, [temp_dir])

    def test_no_restrictions_passes(self, temp_dir):
        """Test that any path passes when no restrictions are set."""
        file_path = Path("/any/random/path/test.png")
        # Should not raise when allowed_paths is None
        _validate_path_access(file_path, None)


class TestReadAndEncode:
    """Test suite for file reading and base64 encoding."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_encode_small_file(self, temp_dir):
        """Test encoding a small file."""
        test_file = temp_dir / "test.png"
        test_content = b"\x89PNG\r\n\x1a\n" + b"fake png data"
        test_file.write_bytes(test_content)

        encoded, mime_type = _read_and_encode(test_file)

        # Verify it's valid base64
        decoded = base64.b64decode(encoded)
        assert decoded == test_content
        assert mime_type == "image/png"


class TestReadMediaTool:
    """Test suite for the main read_media function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_image(self, temp_dir):
        """Create a sample image file for testing."""
        img_path = temp_dir / "test.png"
        # Create a minimal valid PNG (1x1 transparent pixel)
        png_data = bytes(
            [
                0x89,
                0x50,
                0x4E,
                0x47,
                0x0D,
                0x0A,
                0x1A,
                0x0A,  # PNG signature
                0x00,
                0x00,
                0x00,
                0x0D,
                0x49,
                0x48,
                0x44,
                0x52,  # IHDR chunk
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x01,  # 1x1
                0x08,
                0x06,
                0x00,
                0x00,
                0x00,
                0x1F,
                0x15,
                0xC4,
                0x89,
                0x00,
                0x00,
                0x00,
                0x0A,
                0x49,
                0x44,
                0x41,  # IDAT chunk
                0x54,
                0x78,
                0x9C,
                0x63,
                0x00,
                0x01,
                0x00,
                0x00,
                0x05,
                0x00,
                0x01,
                0x0D,
                0x0A,
                0x2D,
                0xB4,
                0x00,
                0x00,
                0x00,
                0x00,
                0x49,
                0x45,
                0x4E,
                0x44,
                0xAE,  # IEND chunk
                0x42,
                0x60,
                0x82,
            ],
        )
        img_path.write_bytes(png_data)
        return img_path

    @pytest.mark.asyncio
    async def test_file_not_found(self, temp_dir):
        """Test that non-existent files return an error."""
        result = await read_media(
            str(temp_dir / "nonexistent.png"),
            agent_cwd=str(temp_dir),
        )

        assert result.output_blocks is not None
        output = result.output_blocks[0].data
        assert "does not exist" in output

    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, temp_dir):
        """Test that unsupported file types return an error."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("hello")

        result = await read_media(
            str(txt_file),
            agent_cwd=str(temp_dir),
        )

        assert result.output_blocks is not None
        output = result.output_blocks[0].data
        assert "Unsupported file type" in output

    @pytest.mark.asyncio
    async def test_native_mm_returns_multimodal_inject(self, temp_dir, sample_image):
        """Test that native MM path returns multimodal_inject metadata."""
        result = await read_media(
            str(sample_image),
            agent_cwd=str(temp_dir),
            backend_type="claude",
            model="claude-sonnet-4-5",
        )

        assert result.output_blocks is not None
        assert result.meta_info is not None
        assert "multimodal_inject" in result.meta_info

        mm_inject = result.meta_info["multimodal_inject"]
        assert mm_inject["type"] == "image"
        assert mm_inject["mime_type"] == "image/png"
        assert "base64" in mm_inject
        # Compare resolved paths to handle macOS /var -> /private/var symlink
        assert Path(mm_inject["source_path"]).resolve() == sample_image.resolve()

    @pytest.mark.asyncio
    async def test_fallback_for_non_mm_model(self, temp_dir, sample_image):
        """Test that non-MM models fall back to understand_image."""
        # Mock understand_image at the source module where it's imported from
        mock_result = AsyncMock()
        mock_result.output_blocks = []

        with patch(
            "massgen.tool._multimodal_tools.understand_image.understand_image",
            return_value=mock_result,
        ) as mock_understand:
            await read_media(
                str(sample_image),
                agent_cwd=str(temp_dir),
                backend_type="openai",
                model="unknown-model-without-vision",  # Not in model_modalities
            )

            # Verify understand_image was called as fallback
            mock_understand.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_for_audio_on_claude(self, temp_dir):
        """Test that audio falls back to understand_audio on Claude (no native audio)."""
        audio_file = temp_dir / "test.mp3"
        audio_file.write_bytes(b"fake mp3 data")

        mock_result = AsyncMock()
        mock_result.output_blocks = []

        with patch(
            "massgen.tool._multimodal_tools.understand_audio.understand_audio",
            return_value=mock_result,
        ) as mock_understand:
            await read_media(
                str(audio_file),
                agent_cwd=str(temp_dir),
                backend_type="claude",
                model="claude-sonnet-4-5",  # Claude doesn't support native audio
            )

            mock_understand.assert_called_once()

    @pytest.mark.asyncio
    async def test_native_audio_on_gemini(self, temp_dir):
        """Test that audio returns multimodal_inject on Gemini (native support)."""
        audio_file = temp_dir / "test.mp3"
        audio_file.write_bytes(b"fake mp3 data")

        result = await read_media(
            str(audio_file),
            agent_cwd=str(temp_dir),
            backend_type="gemini",
            model="gemini-2.5-flash",
        )

        assert result.meta_info is not None
        assert "multimodal_inject" in result.meta_info
        assert result.meta_info["multimodal_inject"]["type"] == "audio"

    @pytest.mark.asyncio
    async def test_native_video_on_gemini(self, temp_dir):
        """Test that video returns multimodal_inject on Gemini (native support)."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"fake mp4 data")

        result = await read_media(
            str(video_file),
            agent_cwd=str(temp_dir),
            backend_type="gemini",
            model="gemini-2.5-flash",
        )

        assert result.meta_info is not None
        assert "multimodal_inject" in result.meta_info
        assert result.meta_info["multimodal_inject"]["type"] == "video"

    @pytest.mark.asyncio
    async def test_relative_path_resolution(self, temp_dir, sample_image):
        """Test that relative paths are resolved correctly."""
        result = await read_media(
            "test.png",  # Relative path
            agent_cwd=str(temp_dir),
            backend_type="claude",
            model="claude-sonnet-4-5",
        )

        assert result.meta_info is not None
        assert "multimodal_inject" in result.meta_info

    @pytest.mark.asyncio
    async def test_prompt_included_in_result(self, temp_dir, sample_image):
        """Test that prompt is included in multimodal_inject."""
        test_prompt = "What is in this image?"

        result = await read_media(
            str(sample_image),
            prompt=test_prompt,
            agent_cwd=str(temp_dir),
            backend_type="claude",
            model="claude-sonnet-4-5",
        )

        assert result.meta_info is not None
        mm_inject = result.meta_info["multimodal_inject"]
        assert mm_inject["prompt"] == test_prompt


class TestModelModalitiesDataclass:
    """Test suite for the ModelModalities dataclass."""

    def test_default_values(self):
        """Test that default values are all False."""
        modalities = ModelModalities()
        assert modalities.image is False
        assert modalities.audio is False
        assert modalities.video is False

    def test_explicit_values(self):
        """Test setting explicit values."""
        modalities = ModelModalities(image=True, audio=True, video=False)
        assert modalities.image is True
        assert modalities.audio is True
        assert modalities.video is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
