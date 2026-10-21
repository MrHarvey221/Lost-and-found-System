"""Preserve valid inline photos from the earlier running prototype as safe files."""
import base64
from io import BytesIO
import json
import logging
from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import select
import models
from uploads import store_upload


async def migrate_inline_photos(sessions, data_dir):
    converted=0
    with sessions() as db:
        for cls in (models.LostItem,models.FoundItem):
            for item in db.scalars(select(cls).where(cls.image_ref.like('data:image/%'))).all():
                original=item.image_ref
                try:
                    header,encoded=original.split(',',1)
                    mime=header.split(';',1)[0].removeprefix('data:')
                    extension={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[mime]
                    raw=base64.b64decode(encoded,validate=True)
                    upload=UploadFile(BytesIO(raw),filename='preserved'+extension,headers=Headers({'content-type':mime}))
                    name=await store_upload(upload,data_dir/'report_images')
                    item.image_ref=name;item.image_refs=json.dumps([name]);converted+=1
                except Exception as error:
                    logging.warning('An original inline photo was retained unchanged because it could not be converted (%s).',type(error).__name__)
        db.commit()
    return converted
