from miniopy_async import Minio
from app.config import settings
from miniopy_async.error import S3Error

def _endpoint() -> str:
    return settings.STORAGE_ENDPOINT.replace("http://", "").replace("https://", "")


def _client() -> Minio:
    return Minio(
        _endpoint(),
        access_key=settings.STORAGE_ACCESS_KEY,
        secret_key=settings.STORAGE_SECRET_KEY,
        secure=False,
    )



async def ensure_bucket() -> None:
    client = _client()

    try:
        exists = await client.bucket_exists(settings.STORAGE_BUCKET)
        if not exists:
            await client.make_bucket(settings.STORAGE_BUCKET)
    except S3Error as e:
        if e.code != "BucketAlreadyOwnedByYou":
            raise

    policy = f"""{{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::{settings.STORAGE_BUCKET}/*"]
        }}]
    }}"""

    await client.set_bucket_policy(settings.STORAGE_BUCKET, policy)


async def upload(key: str, data: bytes) -> None:
    import io
    client = _client()
    await client.put_object(
        settings.STORAGE_BUCKET,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg",
    )


async def delete(key: str) -> None:
    client = _client()
    await client.remove_object(settings.STORAGE_BUCKET, key)
