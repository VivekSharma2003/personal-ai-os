"""
Personal AI OS - PII Scrubbing Service
"""
import re
import logging

logger = logging.getLogger(__name__)

class PIIScrubberService:
    """
    Service to detect and mask Personally Identifiable Information (PII)
    from text using Regex heuristics.
    """
    
    # Simple regex patterns for MVP
    PATTERNS = {
        "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "SSN": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
        "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b'
    }

    def __init__(self, active: bool = True):
        self.active = active

    def scrub_text(self, text: str) -> str:
        """
        Masks detected PII in the given string with placeholders.
        """
        if not self.active or not text:
            return text
            
        scrubbed = text
        
        # Scrub Emails
        scrubbed = re.sub(self.PATTERNS["EMAIL"], '[EMAIL REDACTED]', scrubbed)
        
        # Scrub SSNs
        scrubbed = re.sub(self.PATTERNS["SSN"], '[SSN REDACTED]', scrubbed)
        
        # Scrub Credit Cards (basic heuristic)
        def replace_cc(match):
            val = match.group(0).replace(" ", "").replace("-", "")
            if len(val) >= 13 and len(val) <= 16:
                return '[CREDIT CARD REDACTED]'
            return match.group(0)
            
        scrubbed = re.sub(self.PATTERNS["CREDIT_CARD"], replace_cc, scrubbed)
        
        return scrubbed
