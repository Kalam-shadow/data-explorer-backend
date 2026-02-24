import os
import shutil
from tempfile import NamedTemporaryFile
from fastapi import UploadFile, HTTPException

ALLOWED_EXT = {".xlsx", ".xls", ".csv"}
MAX_FILE_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 20 * 1024 * 1024))  # 20MB default


def _extension_ok(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT


def save_upload_tempfile(upload_file: UploadFile, max_bytes: int = MAX_FILE_BYTES) -> dict:
    if not _extension_ok(upload_file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    # stream to temp file and enforce max size
    tmp = NamedTemporaryFile(delete=False)
    total = 0
    try:
        while True:
            chunk = upload_file.file.read(1024 * 64)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                tmp.close()
                os.unlink(tmp.name)
                raise HTTPException(status_code=413, detail="Uploaded file too large")
            tmp.write(chunk)
        tmp.flush()
        tmp.close()

        return {"path": tmp.name, "size": total, "filename": upload_file.filename, "content_type": upload_file.content_type}
    except HTTPException:
        raise
    except Exception as e:
        try:
            tmp.close()
            os.unlink(tmp.name)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"Failed to save uploaded file: {e}")


def cleanup_tempfile(path: str):
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass
