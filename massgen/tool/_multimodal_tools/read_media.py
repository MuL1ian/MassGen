# -*- coding: utf-8 -*-
"""
Read media files and inject content into conversation context.

This is the primary tool for multimodal input in MassGen. For backends/models
with native multimodal support, it injects base64-encoded media directly into
the tool result. For non-MM models, it falls back to understand_* tools.
"""

import base64
import json
import mimetypes
from pathlib import Path
from typing import List, Optional

from massgen.backend.capabilities import model_supports_media_type
from massgen.logger_config import logger
from massgen.tool._decorators import context_params
from massgen.tool._result import ExecutionResult, TextContent

# Supported media types and their extensions
MEDIA_TYPE_EXTENSIONS = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"},
    "video": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
}

# Session cache to prevent re-injecting the same large media files
# Maps (resolved_path, media_type) -> True if already loaded in this session
_loaded_media_cache: dict[str, bool] = {}


def _detect_media_type(file_path: str) -> Optional[str]:
    """Detect media type from file extension.

    Args:
        file_path: Path to the media file

    Returns:
        Media type string ("image", "audio", "video") or None if unsupported
    """
    ext = Path(file_path).suffix.lower()
    for media_type, extensions in MEDIA_TYPE_EXTENSIONS.items():
        if ext in extensions:
            return media_type
    return None


def _get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        return mime_type

    # Fallback based on extension
    ext = file_path.suffix.lower()
    fallbacks = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
    }
    return fallbacks.get(ext, "application/octet-stream")


def _validate_path_access(path: Path, allowed_paths: Optional[List[Path]] = None) -> None:
    """Validate that a path is within allowed directories.

    Args:
        path: Path to validate
        allowed_paths: List of allowed base paths (optional)

    Raises:
        ValueError: If path is not within allowed directories
    """
    if not allowed_paths:
        return  # No restrictions

    for allowed_path in allowed_paths:
        try:
            path.relative_to(allowed_path)
            return  # Path is within this allowed directory
        except ValueError:
            continue

    raise ValueError(f"Path not in allowed directories: {path}")


def _read_and_encode(file_path: Path) -> tuple[bytes, str]:
    """Read a file and return base64-encoded data with MIME type.

    Args:
        file_path: Path to the media file

    Returns:
        Tuple of (base64_encoded_data, mime_type)
    """
    with open(file_path, "rb") as f:
        data = f.read()

    encoded = base64.b64encode(data).decode("utf-8")
    mime_type = _get_mime_type(file_path)

    return encoded, mime_type


@context_params("backend_type", "model")
async def read_media(
    file_path: str,
    prompt: Optional[str] = None,
    agent_cwd: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    backend_type: Optional[str] = None,
    model: Optional[str] = None,
) -> ExecutionResult:
    """
    Read a media file and inject its content into conversation context.

    For backends/models with native multimodal support, this tool returns the
    media as base64-encoded data that gets injected into the tool result.
    For non-MM models, it falls back to the appropriate understand_* tool
    (understand_image, understand_audio, understand_video) which uses an
    external API to analyze the content.

    Supports:
    - Images: png, jpg, jpeg, gif, webp, bmp
    - Audio: mp3, wav, m4a, ogg, flac, aac
    - Video: mp4, mov, avi, mkv, webm

    Args:
        file_path: Path to the media file (relative or absolute).
                   Relative paths are resolved from agent's working directory.
        prompt: Optional prompt/question about the media content.
                Used when falling back to understand_* tools.
        agent_cwd: Agent's current working directory (automatically injected).
        allowed_paths: List of allowed base paths for validation (optional).
        backend_type: Backend type (automatically injected from ExecutionContext).
        model: Model name (automatically injected from ExecutionContext).

    Returns:
        ExecutionResult containing:
        - For native MM: meta_info["multimodal_inject"] with base64 data
        - For fallback: Text description from understand_* tool

    Examples:
        read_media("screenshot.png")
        → Returns image data for MM models, or description for non-MM

        read_media("recording.mp3", prompt="Transcribe this audio")
        → Returns audio data for MM models, or transcription for non-MM

        read_media("demo.mp4", prompt="What happens in this video?")
        → Returns video data for MM models, or frame analysis for non-MM
    """
    try:
        # Convert allowed_paths from strings to Path objects
        allowed_paths_list = [Path(p) for p in allowed_paths] if allowed_paths else None

        # Resolve file path
        base_dir = Path(agent_cwd) if agent_cwd else Path.cwd()

        if Path(file_path).is_absolute():
            media_path = Path(file_path).resolve()
        else:
            media_path = (base_dir / file_path).resolve()

        # Validate path access
        _validate_path_access(media_path, allowed_paths_list)

        # Check file exists
        if not media_path.exists():
            result = {
                "success": False,
                "operation": "read_media",
                "error": f"File does not exist: {media_path}",
            }
            return ExecutionResult(
                output_blocks=[TextContent(data=json.dumps(result, indent=2))],
            )

        # Detect media type
        media_type = _detect_media_type(file_path)
        if not media_type:
            result = {
                "success": False,
                "operation": "read_media",
                "error": f"Unsupported file type: {media_path.suffix}. Supported: images (png, jpg, gif, webp), audio (mp3, wav, m4a, ogg), video (mp4, mov, avi, mkv, webm)",
            }
            return ExecutionResult(
                output_blocks=[TextContent(data=json.dumps(result, indent=2))],
            )

        # Check if model supports this media type natively
        supports_native = False
        if backend_type and model:
            supports_native = model_supports_media_type(backend_type, model, media_type)
            logger.debug(
                f"Model {backend_type}/{model} native {media_type} support: {supports_native}",
            )

        # If model doesn't support this media type, fall back to understand_* tools
        if not supports_native:
            logger.info(
                f"Model {backend_type}/{model} doesn't support native {media_type}, " f"falling back to understand_{media_type}",
            )

            default_prompt = prompt or f"Please analyze this {media_type} and describe its contents."

            if media_type == "image":
                from massgen.tool._multimodal_tools.understand_image import (
                    understand_image,
                )

                return await understand_image(
                    str(media_path),
                    prompt=default_prompt,
                    agent_cwd=agent_cwd,
                    allowed_paths=allowed_paths,
                )
            elif media_type == "audio":
                from massgen.tool._multimodal_tools.understand_audio import (
                    understand_audio,
                )

                return await understand_audio(
                    audio_paths=[str(media_path)],
                    prompt=default_prompt,
                    backend_type=backend_type,  # Prefer calling agent's backend
                    agent_cwd=agent_cwd,
                    allowed_paths=allowed_paths,
                )
            elif media_type == "video":
                from massgen.tool._multimodal_tools.understand_video import (
                    understand_video,
                )

                return await understand_video(
                    video_path=str(media_path),
                    prompt=default_prompt,
                    backend_type=backend_type,  # Prefer calling agent's backend
                    agent_cwd=agent_cwd,
                    allowed_paths=allowed_paths,
                )

        # Native MM path - model supports this media type
        try:
            encoded_data, mime_type = _read_and_encode(media_path)
            file_size_mb = media_path.stat().st_size / (1024 * 1024)

            logger.info(
                f"Read {media_type} for native MM: {media_path.name} " f"({file_size_mb:.2f}MB, {mime_type})",
            )

            # Return with multimodal_inject metadata
            # The backend's _append_tool_result_message will detect this
            # and format appropriately for the API
            result_text = f"[Media loaded: {media_path.name}]"
            if prompt:
                result_text += f"\nPrompt: {prompt}"

            return ExecutionResult(
                output_blocks=[TextContent(data=result_text)],
                meta_info={
                    "multimodal_inject": {
                        "type": media_type,
                        "base64": encoded_data,
                        "mime_type": mime_type,
                        "source_path": str(media_path),
                        "prompt": prompt,
                    },
                },
            )

        except Exception as read_error:
            result = {
                "success": False,
                "operation": "read_media",
                "error": f"Failed to read media file: {str(read_error)}",
            }
            return ExecutionResult(
                output_blocks=[TextContent(data=json.dumps(result, indent=2))],
            )

    except ValueError as ve:
        # Path validation error
        result = {
            "success": False,
            "operation": "read_media",
            "error": str(ve),
        }
        return ExecutionResult(
            output_blocks=[TextContent(data=json.dumps(result, indent=2))],
        )

    except Exception as e:
        result = {
            "success": False,
            "operation": "read_media",
            "error": f"Failed to read media: {str(e)}",
        }
        return ExecutionResult(
            output_blocks=[TextContent(data=json.dumps(result, indent=2))],
        )
