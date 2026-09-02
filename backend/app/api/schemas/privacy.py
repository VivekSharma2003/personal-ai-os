"""
Personal AI OS - Privacy Schemas
"""
from pydantic import BaseModel

class PrivacySettings(BaseModel):
    pii_scrubbing_enabled: bool

class ScrubRequest(BaseModel):
    text: str
    
class ScrubResponse(BaseModel):
    original_text: str
    scrubbed_text: str
