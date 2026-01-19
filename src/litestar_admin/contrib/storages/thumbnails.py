"""Thumbnail generation for litestar-admin storage.

This module provides server-side thumbnail generation for uploaded images,
supporting multiple output formats and configurable quality settings.

Example:
    Basic usage:

    >>> from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator
    >>>
    >>> generator = ThumbnailGenerator()
    >>> thumbnail = generator.generate(
    ...     image_data=image_bytes,
    ...     size=(200, 200),
    ...     format="webp",
    ...     quality=85,
    ... )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ThumbnailGenerator",
    "ThumbnailResult",
    "ThumbnailSize",
]


@dataclass
class ThumbnailSize:
    """Represents a thumbnail size configuration.

    Attributes:
        width: Maximum width in pixels.
        height: Maximum height in pixels.
        suffix: Suffix to append to thumbnail filenames.
    """

    width: int
    height: int
    suffix: str = ""

    def __post_init__(self) -> None:
        """Validate size values."""
        if self.width < 1:
            msg = "width must be at least 1"
            raise ValueError(msg)
        if self.height < 1:
            msg = "height must be at least 1"
            raise ValueError(msg)

        # Generate default suffix if not provided
        if not self.suffix:
            self.suffix = f"_{self.width}x{self.height}"

    @property
    def as_tuple(self) -> tuple[int, int]:
        """Return size as a (width, height) tuple."""
        return (self.width, self.height)


@dataclass
class ThumbnailResult:
    """Result of thumbnail generation.

    Attributes:
        data: The thumbnail image data as bytes.
        width: Actual width of the generated thumbnail.
        height: Actual height of the generated thumbnail.
        format: The output format (webp, jpeg, png).
        size_bytes: Size of the thumbnail in bytes.
        original_path: The original file path (if applicable).
        thumbnail_path: The generated thumbnail path (if applicable).
    """

    data: bytes
    width: int
    height: int
    format: str
    size_bytes: int
    original_path: str | None = None
    thumbnail_path: str | None = None


@dataclass
class ThumbnailGenerator:
    """Server-side thumbnail generator for uploaded images.

    This class provides methods for generating thumbnails from image data,
    supporting multiple output formats (webp, jpeg, png) with configurable
    quality settings and aspect ratio preservation.

    Attributes:
        default_quality: Default quality for JPEG/WebP output (1-100).
        default_format: Default output format.
        preserve_aspect_ratio: Whether to preserve aspect ratio (fit within box).
        background_color: Background color for images with transparency (RGB tuple).

    Example:
        Synchronous thumbnail generation:

        >>> generator = ThumbnailGenerator(default_quality=90)
        >>> result = generator.generate(image_bytes, size=(200, 200))
        >>> if result:
        ...     save_thumbnail(result.data)

        Async thumbnail generation:

        >>> result = await generator.generate_async(image_bytes, (150, 150))

        Generate multiple sizes:

        >>> sizes = [
        ...     ThumbnailSize(100, 100, "_small"),
        ...     ThumbnailSize(300, 300, "_medium"),
        ...     ThumbnailSize(600, 600, "_large"),
        ... ]
        >>> results = generator.generate_multiple(image_bytes, sizes)
    """

    default_quality: int = 85
    default_format: str = "webp"
    preserve_aspect_ratio: bool = True
    background_color: tuple[int, int, int] = field(default_factory=lambda: (255, 255, 255))

    def __post_init__(self) -> None:
        """Validate configuration."""
        min_quality = 1
        max_quality = 100
        if not min_quality <= self.default_quality <= max_quality:
            msg = f"default_quality must be between {min_quality} and {max_quality}"
            raise ValueError(msg)

        allowed_formats = {"jpeg", "jpg", "png", "webp"}
        if self.default_format.lower() not in allowed_formats:
            msg = f"default_format must be one of: {', '.join(sorted(allowed_formats))}"
            raise ValueError(msg)

    def _convert_for_jpeg(self, img: Any, original_mode: str) -> Any:
        """Convert image to RGB mode for JPEG output.

        Args:
            img: PIL Image object.
            original_mode: Original image mode.

        Returns:
            Converted PIL Image object.
        """
        from PIL import Image

        if original_mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, self.background_color)
            if original_mode == "P":
                img = img.convert("RGBA")
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            return background
        if original_mode != "RGB":
            return img.convert("RGB")
        return img

    def _convert_for_webp(self, img: Any, original_mode: str) -> Any:
        """Convert image to appropriate mode for WebP output.

        Args:
            img: PIL Image object.
            original_mode: Original image mode.

        Returns:
            Converted PIL Image object.
        """
        if original_mode not in ("RGB", "RGBA"):
            return img.convert("RGBA" if original_mode in ("LA", "P") else "RGB")
        return img

    def _convert_for_png(self, img: Any, original_mode: str) -> Any:
        """Convert image to appropriate mode for PNG output.

        Args:
            img: PIL Image object.
            original_mode: Original image mode.

        Returns:
            Converted PIL Image object.
        """
        if original_mode not in ("RGB", "RGBA", "L", "LA"):
            return img.convert("RGBA" if original_mode == "P" else "RGB")
        return img

    def _get_save_kwargs(self, save_format: str, quality: int) -> dict[str, int | bool]:
        """Get kwargs for PIL Image.save() based on format.

        Args:
            save_format: Output format (JPEG, PNG, WEBP).
            quality: Quality setting (1-100).

        Returns:
            Dictionary of kwargs for Image.save().
        """
        save_kwargs: dict[str, int | bool] = {}
        if save_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality
            if save_format == "JPEG":
                save_kwargs["optimize"] = True
        elif save_format == "PNG":
            save_kwargs["optimize"] = True
        return save_kwargs

    def generate(
        self,
        image_data: bytes,
        size: tuple[int, int],
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
    ) -> ThumbnailResult | None:
        """Generate a thumbnail from image data.

        This method creates a thumbnail that fits within the specified size
        while preserving aspect ratio by default.

        Args:
            image_data: The source image data as bytes.
            size: Maximum (width, height) for the thumbnail.
            format: Output format (webp, jpeg, png). Defaults to default_format.
            quality: Quality for JPEG/WebP (1-100). Defaults to default_quality.

        Returns:
            ThumbnailResult containing the thumbnail data and metadata,
            or None if generation fails.

        Example:
            >>> generator = ThumbnailGenerator()
            >>> result = generator.generate(image_bytes, (200, 200), format="webp")
            >>> if result:
            ...     print(f"Generated {result.width}x{result.height} thumbnail")
        """
        try:
            from io import BytesIO

            from PIL import Image
        except ImportError:
            # PIL not installed
            return None

        # Use defaults if not specified
        output_format = (format or self.default_format).lower()
        output_quality = quality if quality is not None else self.default_quality

        try:
            # Open the image
            img = Image.open(BytesIO(image_data))
            original_mode = img.mode

            # Convert to appropriate mode for output format
            if output_format in ("jpeg", "jpg"):
                img = self._convert_for_jpeg(img, original_mode)
            elif output_format == "webp":
                img = self._convert_for_webp(img, original_mode)
            elif output_format == "png":
                img = self._convert_for_png(img, original_mode)

            # Generate thumbnail (maintains aspect ratio)
            if self.preserve_aspect_ratio:
                img.thumbnail(size, Image.Resampling.LANCZOS)
            else:
                # Resize to exact dimensions (may distort)
                img = img.resize(size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = BytesIO()
            save_format = "JPEG" if output_format in ("jpg", "jpeg") else output_format.upper()
            save_kwargs = self._get_save_kwargs(save_format, output_quality)

            img.save(output, format=save_format, **save_kwargs)
            thumbnail_data = output.getvalue()

            return ThumbnailResult(
                data=thumbnail_data,
                width=img.width,
                height=img.height,
                format=output_format,
                size_bytes=len(thumbnail_data),
            )

        except Exception:
            # Any error in processing returns None
            return None

    async def generate_async(
        self,
        image_data: bytes,
        size: tuple[int, int],
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
    ) -> ThumbnailResult | None:
        """Generate a thumbnail asynchronously.

        This method runs the CPU-bound thumbnail generation in a thread pool
        to avoid blocking the event loop.

        Args:
            image_data: The source image data as bytes.
            size: Maximum (width, height) for the thumbnail.
            format: Output format (webp, jpeg, png). Defaults to default_format.
            quality: Quality for JPEG/WebP (1-100). Defaults to default_quality.

        Returns:
            ThumbnailResult containing the thumbnail data and metadata,
            or None if generation fails.

        Example:
            >>> generator = ThumbnailGenerator()
            >>> result = await generator.generate_async(image_bytes, (200, 200))
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(image_data, size, format, quality),
        )

    def generate_multiple(
        self,
        image_data: bytes,
        sizes: Sequence[ThumbnailSize],
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
    ) -> dict[str, ThumbnailResult]:
        """Generate thumbnails at multiple sizes.

        Args:
            image_data: The source image data as bytes.
            sizes: Sequence of ThumbnailSize configurations.
            format: Output format for all thumbnails.
            quality: Quality for all thumbnails.

        Returns:
            Dictionary mapping size suffix to ThumbnailResult.
            Only successful generations are included.

        Example:
            >>> sizes = [
            ...     ThumbnailSize(100, 100, "_sm"),
            ...     ThumbnailSize(400, 400, "_lg"),
            ... ]
            >>> results = generator.generate_multiple(image_bytes, sizes)
            >>> for suffix, result in results.items():
            ...     save_with_suffix(result.data, suffix)
        """
        results: dict[str, ThumbnailResult] = {}

        for size in sizes:
            result = self.generate(image_data, size.as_tuple, format, quality)
            if result:
                results[size.suffix] = result

        return results

    async def generate_multiple_async(
        self,
        image_data: bytes,
        sizes: Sequence[ThumbnailSize],
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
    ) -> dict[str, ThumbnailResult]:
        """Generate thumbnails at multiple sizes asynchronously.

        This method runs all thumbnail generations concurrently in a thread pool.

        Args:
            image_data: The source image data as bytes.
            sizes: Sequence of ThumbnailSize configurations.
            format: Output format for all thumbnails.
            quality: Quality for all thumbnails.

        Returns:
            Dictionary mapping size suffix to ThumbnailResult.
            Only successful generations are included.
        """
        loop = asyncio.get_event_loop()

        async def generate_one(size: ThumbnailSize) -> tuple[str, ThumbnailResult | None]:
            result = await loop.run_in_executor(
                None,
                lambda: self.generate(image_data, size.as_tuple, format, quality),
            )
            return (size.suffix, result)

        tasks = [generate_one(size) for size in sizes]
        completed = await asyncio.gather(*tasks)

        return {suffix: result for suffix, result in completed if result is not None}

    def get_thumbnail_path(
        self,
        original_path: str,
        size: tuple[int, int],
        format: str | None = None,  # noqa: A002
    ) -> str:
        """Generate the storage path for a thumbnail.

        Creates a path based on the original file path with size suffix and
        appropriate extension for the output format.

        Args:
            original_path: The storage path of the original file.
            size: The (width, height) of the thumbnail.
            format: Output format (determines file extension).

        Returns:
            The storage path for the thumbnail.

        Example:
            >>> generator = ThumbnailGenerator()
            >>> path = generator.get_thumbnail_path("uploads/image.jpg", (200, 200))
            'uploads/image_200x200.webp'
            >>> path = generator.get_thumbnail_path("uploads/photo.png", (100, 100), "jpeg")
            'uploads/photo_100x100.jpeg'
        """
        output_format = (format or self.default_format).lower()
        if output_format == "jpg":
            output_format = "jpeg"

        # Split path into directory and filename
        if "/" in original_path:
            directory, filename = original_path.rsplit("/", 1)
        else:
            directory = ""
            filename = original_path

        # Split filename into base name and extension
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

        # Generate size suffix
        width, height = size
        size_suffix = f"_{width}x{height}"

        # Build thumbnail filename
        thumb_filename = f"{base_name}{size_suffix}.{output_format}"

        # Reconstruct full path
        if directory:
            return f"{directory}/{thumb_filename}"
        return thumb_filename

    @staticmethod
    def parse_size_string(size_string: str) -> tuple[int, int] | None:
        """Parse a size string like '200x200' into a (width, height) tuple.

        Args:
            size_string: Size specification in format 'WIDTHxHEIGHT'.

        Returns:
            Tuple of (width, height) or None if parsing fails.

        Example:
            >>> ThumbnailGenerator.parse_size_string("200x150")
            (200, 150)
            >>> ThumbnailGenerator.parse_size_string("invalid")
            None
        """
        try:
            if "x" not in size_string.lower():
                return None
            parts = size_string.lower().split("x")
            if len(parts) != 2:  # noqa: PLR2004
                return None
            width = int(parts[0])
            height = int(parts[1])
            if width < 1 or height < 1:
                return None
            return (width, height)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def is_supported_image(filename: str) -> bool:
        """Check if a filename has a supported image extension.

        Args:
            filename: The filename to check.

        Returns:
            True if the extension is a supported image format.

        Example:
            >>> ThumbnailGenerator.is_supported_image("photo.jpg")
            True
            >>> ThumbnailGenerator.is_supported_image("document.pdf")
            False
        """
        supported = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[-1].lower()
        return ext in supported
