"""FilesController for file upload and management.

This module provides REST API endpoints for file uploads, downloads, and deletion
in the admin panel.

Example:
    The controller is automatically registered by AdminPlugin.
    Access endpoints at:
    - POST /admin/api/files/upload - Upload a file
    - DELETE /admin/api/files/{path:path} - Delete a file
    - GET /admin/api/files/{path:path} - Serve or redirect to a file
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from litestar import Controller, delete, get, post
from litestar.datastructures import UploadFile  # noqa: TC002  # Required for runtime signature
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotFoundException
from litestar.params import Body
from litestar.response import Redirect, Response
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from litestar_admin.fields.file import (
    FileField,
    ImageField,
    validate_file_field,
)

if TYPE_CHECKING:
    from litestar_admin.contrib.storages import AdminStorageBackend

__all__ = [
    "DeleteFileResponse",
    "FileInfoResponse",
    "FilesController",
    "UploadFileRequest",
    "UploadFileResponse",
]


@dataclass
class UploadFileRequest:
    """Request body for file upload.

    Attributes:
        model_name: The name of the model this file belongs to.
        field_name: The name of the field this file belongs to.
    """

    model_name: str
    field_name: str


@dataclass
class UploadFileResponse:
    """Response for successful file upload.

    Attributes:
        success: Whether the upload was successful.
        storage_path: The path where the file was stored.
        original_filename: The original filename from the upload.
        file_size: The size of the file in bytes.
        content_type: The MIME type of the file.
        public_url: The public URL to access the file.
        thumbnail_path: Path to the generated thumbnail (for images).
        thumbnail_url: URL to access the thumbnail (for images).
    """

    success: bool
    storage_path: str
    original_filename: str
    file_size: int
    content_type: str | None = None
    public_url: str | None = None
    thumbnail_path: str | None = None
    thumbnail_url: str | None = None


@dataclass
class DeleteFileResponse:
    """Response for file deletion.

    Attributes:
        success: Whether the deletion was successful.
        path: The path of the deleted file.
        message: Optional message about the deletion.
    """

    success: bool
    path: str
    message: str | None = None


@dataclass
class FileInfoResponse:
    """Response with file information.

    Attributes:
        exists: Whether the file exists.
        path: The storage path of the file.
        public_url: The public URL to access the file.
    """

    exists: bool
    path: str
    public_url: str | None = None


@dataclass
class ValidationErrorResponse:
    """Response for validation errors.

    Attributes:
        success: Always False for validation errors.
        errors: List of validation error details.
    """

    success: bool
    errors: list[dict[str, str]]


class FilesController(Controller):
    """Controller for file upload and management.

    Provides endpoints for uploading, serving, and deleting files.
    Integrates with the storage backend system and file field validation.

    Example:
        The controller is automatically registered by AdminPlugin.
        Upload a file::

            POST /admin/api/files/upload
            Content-Type: multipart/form-data

            file: <binary>
            model_name: "user"
            field_name: "avatar"
    """

    path = "/api/files"
    tags: ClassVar[list[str]] = ["Files"]

    @post(
        "/upload",
        status_code=HTTP_201_CREATED,
        summary="Upload a file",
        description="Upload a file for a specific model field.",
    )
    async def upload_file(
        self,
        admin_storage: AdminStorageBackend,
        data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
        model_name: str = Body(),
        field_name: str = Body(),
        allowed_extensions: str | None = Body(default=None),
        max_size: int | None = Body(default=None),
        generate_thumbnail: bool = Body(default=False),  # noqa: FBT001
    ) -> UploadFileResponse | Response[ValidationErrorResponse]:
        """Upload a file for a model field.

        This endpoint handles file uploads with validation against the provided
        field configuration. It supports both regular files and images with
        optional thumbnail generation.

        Args:
            admin_storage: The storage backend for file operations.
            data: The uploaded file from the multipart form.
            model_name: The name of the model this file belongs to.
            field_name: The name of the field this file belongs to.
            allowed_extensions: Comma-separated list of allowed extensions.
            max_size: Maximum file size in bytes.
            generate_thumbnail: Whether to generate a thumbnail (for images).

        Returns:
            UploadFileResponse on success, or validation error response.

        Raises:
            ValidationException: If the file fails validation.
        """
        # Build field configuration from request parameters
        extensions_list = None
        if allowed_extensions:
            extensions_list = [ext.strip() for ext in allowed_extensions.split(",")]

        if generate_thumbnail:
            field_config: FileField = ImageField(
                name=field_name,
                allowed_extensions=extensions_list,
                max_size=max_size,
                generate_thumbnail=True,
            )
        else:
            field_config = FileField(
                name=field_name,
                allowed_extensions=extensions_list,
                max_size=max_size,
            )

        # Read file content
        file_content = await data.read()

        # Validate the file
        validation_errors = validate_file_field(data, field_config, file_content=file_content)

        if validation_errors:
            return Response(
                content=ValidationErrorResponse(
                    success=False,
                    errors=[
                        {
                            "field": err.field_name,
                            "error": err.error,
                            "code": err.error_code,
                        }
                        for err in validation_errors
                    ],
                ),
                status_code=422,
            )

        # Upload the file
        if isinstance(field_config, ImageField) and field_config.generate_thumbnail:
            storage_path, thumbnail_path = await admin_storage.upload_with_thumbnail(
                file_content=file_content,
                filename=data.filename or "unnamed",
                model_name=model_name,
                field_name=field_name,
            )
            thumbnail_url = (
                admin_storage.get_public_url(thumbnail_path) if thumbnail_path else None
            )
        else:
            storage_path = await admin_storage.upload(
                file_content=file_content,
                filename=data.filename or "unnamed",
                model_name=model_name,
                field_name=field_name,
            )
            thumbnail_path = None
            thumbnail_url = None

        public_url = admin_storage.get_public_url(storage_path)

        return UploadFileResponse(
            success=True,
            storage_path=storage_path,
            original_filename=data.filename or "unnamed",
            file_size=len(file_content),
            content_type=data.content_type,
            public_url=public_url,
            thumbnail_path=thumbnail_path,
            thumbnail_url=thumbnail_url,
        )

    @post(
        "/upload/validate",
        status_code=HTTP_200_OK,
        summary="Validate file upload",
        description="Validate a file against field configuration without uploading.",
    )
    async def validate_upload(
        self,
        data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
        field_name: str = Body(),
        allowed_extensions: str | None = Body(default=None),
        max_size: int | None = Body(default=None),
        is_image: bool = Body(default=False),  # noqa: FBT001
        required: bool = Body(default=False),  # noqa: FBT001
    ) -> dict[str, Any]:
        """Validate a file without uploading.

        This endpoint allows pre-validation of files before actual upload,
        useful for client-side validation feedback.

        Args:
            data: The uploaded file to validate.
            field_name: The name of the field for error reporting.
            allowed_extensions: Comma-separated list of allowed extensions.
            max_size: Maximum file size in bytes.
            is_image: Whether this is an image field.
            required: Whether the field is required.

        Returns:
            Dictionary with validation result and any errors.
        """
        extensions_list = None
        if allowed_extensions:
            extensions_list = [ext.strip() for ext in allowed_extensions.split(",")]

        if is_image:
            field_config: FileField = ImageField(
                name=field_name,
                allowed_extensions=extensions_list,
                max_size=max_size,
                required=required,
            )
        else:
            field_config = FileField(
                name=field_name,
                allowed_extensions=extensions_list,
                max_size=max_size,
                required=required,
            )

        # Read file content for size validation
        file_content = await data.read()

        # Validate
        validation_errors = validate_file_field(data, field_config, file_content=file_content)

        if validation_errors:
            return {
                "valid": False,
                "errors": [
                    {
                        "field": err.field_name,
                        "error": err.error,
                        "code": err.error_code,
                    }
                    for err in validation_errors
                ],
            }

        return {
            "valid": True,
            "file_info": {
                "filename": data.filename,
                "size": len(file_content),
                "content_type": data.content_type,
            },
        }

    @delete(
        "/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Delete a file",
        description="Delete a file from storage by its path.",
    )
    async def delete_file(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
    ) -> DeleteFileResponse:
        """Delete a file from storage.

        Args:
            file_path: The storage path of the file to delete.
            admin_storage: The storage backend for file operations.

        Returns:
            DeleteFileResponse indicating success or failure.

        Raises:
            NotFoundException: If the file does not exist.
        """
        # Check if file exists
        if not await admin_storage.exists(file_path):
            raise NotFoundException(f"File not found: {file_path}")

        # Delete the file
        await admin_storage.delete(file_path)

        return DeleteFileResponse(
            success=True,
            path=file_path,
            message="File deleted successfully",
        )

    @get(
        "/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Get file or redirect",
        description="Serve a file or redirect to its storage URL.",
    )
    async def get_file(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
        download: bool = False,  # noqa: FBT001, FBT002
    ) -> Response[bytes] | Redirect:
        """Get a file from storage.

        This endpoint either serves the file directly or redirects to its
        public URL depending on the storage configuration.

        Args:
            file_path: The storage path of the file.
            admin_storage: The storage backend for file operations.
            download: If True, force download with Content-Disposition header.

        Returns:
            File content or redirect to public URL.

        Raises:
            NotFoundException: If the file does not exist.
        """
        # Check if file exists
        if not await admin_storage.exists(file_path):
            raise NotFoundException(f"File not found: {file_path}")

        # Get public URL
        public_url = admin_storage.get_public_url(file_path)

        # If we have a public URL that's not a relative path, redirect
        if public_url.startswith(("http://", "https://")):
            return Redirect(path=public_url)

        # Otherwise, serve the file directly
        content = await admin_storage.read(file_path)

        # Determine content type from extension
        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        content_type = _get_content_type(filename)

        headers = {}
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return Response(
            content=content,
            media_type=content_type,
            headers=headers,
        )

    @get(
        "/info/{file_path:path}",
        status_code=HTTP_200_OK,
        summary="Get file info",
        description="Get information about a file without downloading it.",
    )
    async def get_file_info(
        self,
        file_path: str,
        admin_storage: AdminStorageBackend,
    ) -> FileInfoResponse:
        """Get information about a file.

        Args:
            file_path: The storage path of the file.
            admin_storage: The storage backend for file operations.

        Returns:
            FileInfoResponse with file existence and URL.
        """
        exists = await admin_storage.exists(file_path)
        public_url = admin_storage.get_public_url(file_path) if exists else None

        return FileInfoResponse(
            exists=exists,
            path=file_path,
            public_url=public_url,
        )


def _get_content_type(filename: str) -> str:
    """Get the MIME content type for a filename.

    Args:
        filename: The filename to get the content type for.

    Returns:
        The MIME content type string.
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    content_types = {
        # Images
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "ico": "image/x-icon",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        # Documents
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "csv": "text/csv",
        "rtf": "application/rtf",
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "odp": "application/vnd.oasis.opendocument.presentation",
        # Archives
        "zip": "application/zip",
        "tar": "application/x-tar",
        "gz": "application/gzip",
        "7z": "application/x-7z-compressed",
        "rar": "application/vnd.rar",
        # Text/Code
        "json": "application/json",
        "xml": "application/xml",
        "yaml": "application/x-yaml",
        "yml": "application/x-yaml",
        "md": "text/markdown",
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript",
    }

    return content_types.get(extension, "application/octet-stream")
