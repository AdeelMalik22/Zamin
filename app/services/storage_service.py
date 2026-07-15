from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.exceptions.custom_exceptions import ValidationAppError
from app.utils.helpers import new_uuid


@dataclass(frozen=True, slots=True)
class PreparedImage:
    content: bytes
    extension: str


@dataclass(frozen=True, slots=True)
class StoredImage:
    image_id: str
    image_url: str
    disk_path: Path


def detect_image_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


class LocalListingStorage:
    async def prepare_images(self, files: list[UploadFile]) -> list[PreparedImage]:
        if not files:
            raise ValidationAppError("at least one image is required")
        prepared: list[PreparedImage] = []
        mime_by_extension = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        for upload in files:
            try:
                content = await upload.read(settings.max_image_bytes + 1)
            finally:
                await upload.close()
            if not content:
                raise ValidationAppError("an uploaded image is empty")
            if len(content) > settings.max_image_bytes:
                max_megabytes = settings.max_image_bytes // (1024 * 1024)
                raise ValidationAppError(f"each image must be no larger than {max_megabytes} MB")
            extension = detect_image_type(content)
            if extension is None:
                raise ValidationAppError("only JPEG, PNG, and WEBP image content is accepted")
            supplied_mime = (upload.content_type or "").lower()
            if supplied_mime and supplied_mime != mime_by_extension[extension]:
                raise ValidationAppError("uploaded file MIME type does not match its image content")
            prepared.append(PreparedImage(content=content, extension=extension))
        return prepared

    def store_images(self, listing_id: str, images: list[PreparedImage]) -> list[StoredImage]:
        destination = settings.media_root / "listings" / listing_id
        destination.mkdir(parents=True, exist_ok=True)
        stored: list[StoredImage] = []
        try:
            for image in images:
                image_id = new_uuid()
                filename = f"{image_id}.{image.extension}"
                disk_path = destination / filename
                with disk_path.open("xb") as target:
                    target.write(image.content)
                stored.append(
                    StoredImage(
                        image_id=image_id,
                        image_url=f"/media/listings/{listing_id}/{filename}",
                        disk_path=disk_path,
                    )
                )
        except Exception:
            for item in stored:
                item.disk_path.unlink(missing_ok=True)
            raise
        return stored

    def delete_image(self, image_url: str) -> None:
        prefix = "/media/"
        if not image_url.startswith(prefix):
            return
        path = (settings.media_root / image_url.removeprefix(prefix)).resolve()
        try:
            path.relative_to(settings.media_root)
        except ValueError:
            return
        path.unlink(missing_ok=True)
