# -*- coding: utf-8 -*-
"""
Unified media generation tool.

This is the main entry point for all media generation in MassGen.
It automatically selects the best available backend based on:
1. Explicit `backend` parameter
2. `multimodal_config` overrides
3. Available API keys and priority order
"""
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from massgen.logger_config import logger
from massgen.tool._decorators import context_params
from massgen.tool._multimodal_tools.generation._audio import generate_audio
from massgen.tool._multimodal_tools.generation._base import (
    GenerationConfig,
    MediaType,
    get_default_model,
    has_api_key,
)
from massgen.tool._multimodal_tools.generation._image import generate_image
from massgen.tool._multimodal_tools.generation._selector import (
    get_available_backends_hint,
    select_backend_and_model,
)
from massgen.tool._multimodal_tools.generation._video import generate_video
from massgen.tool._result import ExecutionResult, TextContent


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


_ALLOWED_INPUT_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
_MAX_INPUT_IMAGE_SIZE_BYTES = 4 * 1024 * 1024  # 4MB limit for Requests API


def _prepare_input_images(
    image_paths: List[str],
    base_dir: Path,
    allowed_paths: Optional[List[Path]] = None,
) -> tuple[list[dict[str, str]], list[str]]:
    """Validate and load input images for image-to-image generation.

    Returns a tuple of (content blocks, resolved_paths).
    """

    content_blocks: list[dict[str, str]] = []
    resolved_paths: list[str] = []

    for image_path_str in image_paths:
        if Path(image_path_str).is_absolute():
            resolved_path = Path(image_path_str).resolve()
        else:
            resolved_path = (base_dir / image_path_str).resolve()

        _validate_path_access(resolved_path, allowed_paths)

        if not resolved_path.exists():
            raise ValueError(f"Input image does not exist: {resolved_path}")

        if resolved_path.suffix.lower() not in _ALLOWED_INPUT_IMAGE_SUFFIXES:
            allowed = ", ".join(sorted(_ALLOWED_INPUT_IMAGE_SUFFIXES))
            raise ValueError(f"Input image must be one of [{allowed}]: {resolved_path}")

        file_size = resolved_path.stat().st_size
        if file_size > _MAX_INPUT_IMAGE_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            raise ValueError(
                f"Input image too large ({size_mb:.2f}MB). Maximum is {_MAX_INPUT_IMAGE_SIZE_BYTES / (1024 * 1024):.0f}MB: {resolved_path}",
            )

        image_bytes = resolved_path.read_bytes()
        mime_type = "image/jpeg" if resolved_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        content_blocks.append(
            {
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{image_base64}",
            },
        )
        resolved_paths.append(str(resolved_path))

    return content_blocks, resolved_paths


def _clean_for_filename(text: str, max_length: int = 30) -> str:
    """Clean text for use in filename.

    Args:
        text: Text to clean
        max_length: Maximum length of cleaned text

    Returns:
        Cleaned text suitable for filenames
    """
    clean = "".join(c for c in text[:max_length] if c.isalnum() or c in (" ", "-", "_")).strip()
    return clean.replace(" ", "_")


def _get_extension(media_type: MediaType, audio_format: Optional[str] = None) -> str:
    """Get file extension for media type.

    Args:
        media_type: Type of media
        audio_format: For audio, the specific format

    Returns:
        File extension without dot
    """
    if media_type == MediaType.IMAGE:
        return "png"
    elif media_type == MediaType.VIDEO:
        return "mp4"
    elif media_type == MediaType.AUDIO:
        return audio_format or "mp3"
    return "bin"


@context_params("agent_cwd", "allowed_paths", "multimodal_config")
async def generate_media(
    prompt: str,
    mode: Literal["image", "video", "audio"],
    input_images: Optional[List[str]] = None,
    storage_path: Optional[str] = None,
    backend: Optional[str] = None,
    model: Optional[str] = None,
    quality: Optional[str] = None,
    duration: Optional[int] = None,
    voice: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    audio_format: Optional[str] = None,
    instructions: Optional[str] = None,
    extra_params: Optional[Dict[str, Any]] = None,
    agent_cwd: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    multimodal_config: Optional[Dict[str, Any]] = None,
) -> ExecutionResult:
    """
    Generate media (image, video, or audio) from a text prompt.

    This is the unified entry point for all media generation in MassGen.
    It automatically selects the best available backend based on:
    1. Explicit `backend` parameter
    2. `multimodal_config` overrides
    3. Available API keys and priority order

    Args:
        prompt: Text description of what to generate (or text to speak for audio)
        mode: Type of media to generate - "image", "video", or "audio"
        input_images: Optional list of image paths for image-to-image (OpenAI Responses API)
        storage_path: Directory to save generated media (optional)
                     - Relative paths resolved from agent workspace
                     - Absolute paths must be in allowed directories
                     - Defaults to agent workspace root
        backend: Preferred backend ("openai", "google", "openrouter", or "auto")
                 Falls back to others if unavailable
        model: Override the default model for the selected backend
        quality: Quality setting ("standard", "hd") - backend-specific
        duration: For video/audio: length in seconds
        voice: For audio: voice ID (e.g., "alloy", "echo", "nova", "shimmer")
        aspect_ratio: For image/video: aspect ratio (e.g., "16:9", "1:1")
        audio_format: For audio: output format (mp3, wav, opus, etc.)
        instructions: For audio: speaking instructions (tone, style)
        extra_params: Backend-specific parameters
        agent_cwd: Agent's working directory (auto-injected)
        allowed_paths: Allowed directories for output (auto-injected)
        multimodal_config: Per-modality backend/model overrides (auto-injected)

    Returns:
        ExecutionResult with generated file info or error

    Examples:
        # Generate an image
        generate_media("a cat in space", mode="image")

        # Generate video with Google Veo
        generate_media(
            "A robot walking through a city",
            mode="video",
            backend="google",
            duration=8
        )

        # Generate audio with specific voice
        generate_media(
            "Hello world!",
            mode="audio",
            voice="nova"
        )

    Supported Backends:
        Image: openai (GPT-4.1), google (Imagen), openrouter
        Video: google (Veo), openai (Sora-2)
        Audio: openai (gpt-4o-mini-tts)
    """
    try:
        # Parse mode to MediaType
        try:
            media_type = MediaType(mode)
        except ValueError:
            return _error_result(
                f"Invalid mode '{mode}'. Must be 'image', 'video', or 'audio'",
            )

        base_dir = Path(agent_cwd) if agent_cwd else Path.cwd()
        allowed_paths_list = [Path(p) for p in allowed_paths] if allowed_paths else None

        # Select backend and model (using config defaults when not specified)
        selected_backend, selected_model = select_backend_and_model(
            media_type=media_type,
            preferred_backend=backend,
            preferred_model=model,
            config=multimodal_config,
        )

        if not selected_backend:
            hint = get_available_backends_hint(media_type)
            return _error_result(f"No backend available for {mode} generation. {hint}")

        # Optional: process input images for image-to-image generation (OpenAI only)
        input_image_content: List[Dict[str, str]] = []
        input_image_paths: List[str] = []
        if media_type == MediaType.IMAGE and input_images:
            backend_forced_to_openai = False

            if selected_backend != "openai":
                if has_api_key("openai"):
                    backend_forced_to_openai = True
                    selected_backend = "openai"
                else:
                    return _error_result(
                        "Input images currently require the OpenAI backend (Responses API). " "Please set OPENAI_API_KEY to enable image-to-image generation.",
                    )

            input_image_content, input_image_paths = _prepare_input_images(
                input_images,
                base_dir,
                allowed_paths_list,
            )

            if backend_forced_to_openai:
                selected_model = get_default_model("openai", media_type)
            elif selected_backend == "openai":
                selected_model = selected_model or get_default_model("openai", media_type)

        # Resolve output path
        if storage_path:
            if Path(storage_path).is_absolute():
                output_dir = Path(storage_path).resolve()
            else:
                output_dir = (base_dir / storage_path).resolve()
        else:
            output_dir = base_dir

        # Validate path access
        _validate_path_access(output_dir, allowed_paths_list)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_prompt = _clean_for_filename(prompt)
        ext = _get_extension(media_type, audio_format)
        filename = f"{timestamp}_{clean_prompt}.{ext}"
        output_path = output_dir / filename

        # Build config (selected_model includes priority: user param > config > default)
        config = GenerationConfig(
            prompt=prompt,
            output_path=output_path,
            media_type=media_type,
            backend=selected_backend,
            model=selected_model,
            quality=quality,
            duration=duration,
            voice=voice,
            aspect_ratio=aspect_ratio,
            extra_params=extra_params or {},
            input_images=input_image_content,
            input_image_paths=input_image_paths,
        )

        # Add instructions to extra_params for audio
        if instructions and media_type == MediaType.AUDIO:
            config.extra_params["instructions"] = instructions

        # Execute generation based on media type
        if media_type == MediaType.IMAGE:
            result = await generate_image(config)
        elif media_type == MediaType.VIDEO:
            result = await generate_video(config)
        elif media_type == MediaType.AUDIO:
            result = await generate_audio(config)
        else:
            return _error_result(f"Unsupported media type: {mode}")

        # Return result
        if result.success:
            metadata = dict(result.metadata or {})
            if input_image_paths:
                metadata["input_image_paths"] = input_image_paths

            return ExecutionResult(
                output_blocks=[
                    TextContent(
                        data=json.dumps(
                            {
                                "success": True,
                                "operation": "generate_media",
                                "mode": mode,
                                "file_path": str(result.output_path),
                                "filename": result.output_path.name if result.output_path else None,
                                "backend": result.backend_name,
                                "model": result.model_used,
                                "file_size": result.file_size_bytes,
                                "duration_seconds": result.duration_seconds,
                                "metadata": metadata,
                            },
                            indent=2,
                        ),
                    ),
                ],
            )
        else:
            return _error_result(result.error or "Generation failed")

    except ValueError as e:
        return _error_result(str(e))
    except Exception as e:
        logger.exception(f"generate_media failed: {e}")
        return _error_result(f"Generation error: {str(e)}")


def _error_result(error: str) -> ExecutionResult:
    """Create an error ExecutionResult.

    Args:
        error: Error message

    Returns:
        ExecutionResult with error info
    """
    return ExecutionResult(
        output_blocks=[
            TextContent(
                data=json.dumps(
                    {
                        "success": False,
                        "operation": "generate_media",
                        "error": error,
                    },
                    indent=2,
                ),
            ),
        ],
    )
