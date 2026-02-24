from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[Any]] = []


class FileMeta(BaseModel):
    filename: str
    content_type: Optional[str]
    size: Optional[int]


class RowValidationError(BaseModel):
    row_index: int
    errors: Dict[str, str]


class ParsedDataResponse(BaseModel):
    file: FileMeta
    detected_columns: List[str]
    row_count: int
    preview: List[Dict[str, Any]]
    validation_errors: Optional[List[RowValidationError]] = []


class UploadResponse(APIResponse):
    data: Optional[ParsedDataResponse] = None
