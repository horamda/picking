import hashlib
from datetime import datetime

from models import UploadedFile


def create_uploaded_file_record(
    file_bytes: bytes,
    filename: str,
    category: str,
    content_type: str | None = None,
    original_filename: str | None = None,
    batch_id: int | None = None,
    status: str = 'recibido',
) -> UploadedFile:
    return UploadedFile(
        batch_id=batch_id,
        filename=filename,
        original_filename=original_filename or filename,
        category=category,
        content_type=content_type,
        size_bytes=len(file_bytes),
        checksum_sha256=hashlib.sha256(file_bytes).hexdigest(),
        data=file_bytes,
        status=status,
    )


def mark_uploaded_file(uploaded_file: UploadedFile, status: str, error_message: str | None = None) -> UploadedFile:
    uploaded_file.status = status
    uploaded_file.error_message = error_message
    uploaded_file.processed_at = datetime.utcnow()
    return uploaded_file


def uploaded_file_to_dict(uploaded_file: UploadedFile) -> dict:
    return {
        'id': uploaded_file.id,
        'batch_id': uploaded_file.batch_id,
        'filename': uploaded_file.filename,
        'original_filename': uploaded_file.original_filename,
        'category': uploaded_file.category,
        'content_type': uploaded_file.content_type,
        'size_bytes': uploaded_file.size_bytes,
        'checksum_sha256': uploaded_file.checksum_sha256,
        'status': uploaded_file.status,
        'error_message': uploaded_file.error_message,
        'created_at': uploaded_file.created_at.isoformat() if uploaded_file.created_at else None,
        'processed_at': uploaded_file.processed_at.isoformat() if uploaded_file.processed_at else None,
    }
