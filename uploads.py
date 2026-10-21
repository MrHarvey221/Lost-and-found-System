"""Bounded, validated uploads with opaque names outside the static frontend."""
from io import BytesIO
from pathlib import Path
import re
import uuid
import warnings
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 3 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 16_000_000


async def store_upload(upload: UploadFile, directory: Path, evidence=False):
    raw = await upload.read(MAX_BYTES + 1)
    await upload.close()
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(422, 'Choose a non-empty file no larger than 3 MB.')
    suffix = Path(upload.filename or '').suffix.lower()
    mime = upload.content_type or ''
    if evidence and suffix == '.pdf' and mime == 'application/pdf' and raw.startswith(b'%PDF-') and b'%%EOF' in raw[-2048:]:
        data, extension = raw, '.pdf'
    else:
        if suffix not in {'.jpg', '.jpeg', '.png', '.webp'} or mime not in {'image/jpeg','image/png','image/webp'}:
            raise HTTPException(422, 'Use JPG, PNG or WEBP; private evidence may also be PDF.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    if image.format not in {'JPEG','PNG','WEBP'}:
                        raise ValueError('Unsupported image')
                    image.load()
                    image.thumbnail((2400, 2400))
                    clean = image.convert('RGB')
                    output = BytesIO()
                    clean.save(output, format='JPEG', quality=88)  # strips EXIF and other metadata
                    data, extension = output.getvalue(), '.jpg'
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise HTTPException(422, 'The file is not a valid, reasonably sized image.')
    directory.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + extension
    path = directory / name
    path.write_bytes(data)
    return name


def upload_path(directory: Path, name: str | None):
    if not name or not re.fullmatch(r'[a-f0-9]{32}\.(?:jpg|pdf)', name):
        raise HTTPException(404, 'File unavailable. Legacy file references must be re-uploaded.')
    path = directory / name
    if not path.is_file():
        raise HTTPException(404, 'File not found.')
    return path
