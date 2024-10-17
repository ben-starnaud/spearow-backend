from pydantic import BaseModel

class UploadData(BaseModel):
    filename: str
    content: str
    format_type: str  # New field to store the format type (e.g., JSON, XML, SQL)

    class Config:
        schema_extra = {
            "example": {
                "filename": "data.json",
                "content": '{"key": "value"}',
                "format_type": "json"
            }
        }