# -*- coding: utf-8 -*-
"""
Read media files and analyze them using understand_* tools.

This is the primary tool for multimodal input in MassGen. It delegates to
understand_image, understand_audio, or understand_video based on file type.
These tools make external API calls to analyze the media content.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from massgen.logger_config import logger
from massgen.tool._decorators import context_params
from massgen.tool._result import ExecutionResult, TextContent

# Supported media types and their extensions
MEDIA_TYPE_EXTENSIONS = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"},
    "video": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
}


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


@context_params("backend_type", "model")
async def read_media(
    file_path: str,
    prompt: Optional[str] = None,
    agent_cwd: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    backend_type: Optional[str] = None,
    model: Optional[str] = None,
    multimodal_config: Optional[Dict[str, Any]] = None,
) -> ExecutionResult:
    """
    Read and analyze a media file using external API calls.

    This tool delegates to understand_image, understand_audio, or understand_video
    based on the file type. These tools make external API calls to analyze the
    media content and return text descriptions.

    Supports:
    - Images: png, jpg, jpeg, gif, webp, bmp
    - Audio: mp3, wav, m4a, ogg, flac, aac
    - Video: mp4, mov, avi, mkv, webm

    Args:
        file_path: Path to the media file (relative or absolute).
                   Relative paths are resolved from agent's working directory.
        prompt: Optional prompt/question about the media content.
        agent_cwd: Agent's current working directory (automatically injected).
        allowed_paths: List of allowed base paths for validation (optional).
        backend_type: Backend type (automatically injected from ExecutionContext).
        model: Model name (automatically injected from ExecutionContext).
        multimodal_config: Optional config overrides per modality. Format:
            {
                "audio": {"backend": "openai", "model": "gpt-4o-transcribe"},
                "video": {"backend": "gemini", "model": "gemini-3-flash-preview"},
                "image": {"backend": "openai", "model": "gpt-4.1"}
            }

    Returns:
        ExecutionResult containing text description/analysis of the media

    Examples:
        read_media("screenshot.png")
        → Returns description of the image

        read_media("recording.mp3", prompt="Transcribe this audio")
        → Returns transcription of the audio

        read_media("demo.mp4", prompt="What happens in this video?")
        → Returns description based on video frame analysis
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

        # Use understand_* tools for all media analysis (external API calls)
        # This provides consistent, reliable behavior across all backends
        logger.info(f"Using understand_{media_type} for {media_type} analysis")

        default_prompt = prompt or f"Please analyze this {media_type} and describe its contents."

        # Extract config overrides for this media type
        media_config = (multimodal_config or {}).get(media_type, {})
        override_backend = media_config.get("backend") or backend_type
        override_model = media_config.get("model")

        if media_config:
            logger.info(f"Using multimodal_config override for {media_type}: {media_config}")

        if media_type == "image":
            from massgen.tool._multimodal_tools.understand_image import understand_image

            return await understand_image(
                str(media_path),
                prompt=default_prompt,
                agent_cwd=agent_cwd,
                allowed_paths=allowed_paths,
            )
        elif media_type == "audio":
            from massgen.tool._multimodal_tools.understand_audio import understand_audio

            return await understand_audio(
                audio_paths=[str(media_path)],
                prompt=default_prompt,
                backend_type=override_backend,
                model=override_model,
                agent_cwd=agent_cwd,
                allowed_paths=allowed_paths,
            )
        elif media_type == "video":
            from massgen.tool._multimodal_tools.understand_video import understand_video

            return await understand_video(
                video_path=str(media_path),
                prompt=default_prompt,
                backend_type=override_backend,
                model=override_model,
                agent_cwd=agent_cwd,
                allowed_paths=allowed_paths,
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
