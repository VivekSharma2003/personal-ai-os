"""
Personal AI OS - Portability Service
"""
import json
import base64
import logging
from typing import List, Dict, Any
from uuid import UUID
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.rule import Rule, RuleStatus
from app.services.rule_engine import RuleEngineService

logger = logging.getLogger(__name__)

class PortabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.rule_engine = RuleEngineService(db)
        
        # Derive a 32-byte key for Fernet from the application secret
        secret = getattr(self.settings, 'secret_key', 'default-ai-os-secret-key').encode('utf-8')
        padded_secret = secret.ljust(32, b'0')[:32]
        self.fernet = Fernet(base64.urlsafe_b64encode(padded_secret))

    async def export_rules(self, user_id: UUID, encrypt: bool = True) -> str:
        """Export user's active rules to a JSON string or encrypted token."""
        rules = await self.rule_engine.get_user_rules(user_id, status=RuleStatus.ACTIVE.value)
        
        export_data = []
        for r in rules:
            export_data.append({
                "content": r.content,
                "category": r.category,
                "confidence": r.confidence
            })
            
        payload = json.dumps({"rules": export_data})
        
        if encrypt:
            return self.fernet.encrypt(payload.encode('utf-8')).decode('utf-8')
        return payload

    async def import_rules(self, user_id: UUID, payload: str, is_encrypted: bool = True) -> Dict[str, Any]:
        """Import rules from an exported payload."""
        try:
            if is_encrypted:
                decrypted_bytes = self.fernet.decrypt(payload.encode('utf-8'))
                data = json.loads(decrypted_bytes.decode('utf-8'))
            else:
                data = json.loads(payload)
                
            rules_data = data.get("rules", [])
            
            imported_count = 0
            for item in rules_data:
                await self.rule_engine.create_rule(
                    user_id=user_id,
                    content=item.get("content"),
                    category=item.get("category", "general"),
                    original_correction="Imported via portability sync"
                )
                imported_count += 1
                
            await self.db.commit()
            
            return {
                "status": "success",
                "imported_count": imported_count
            }
            
        except Exception as e:
            logger.error(f"Error importing rules: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to parse or decrypt payload. Ensure the key and format are correct."
            }
