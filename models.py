from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Opportunity:
    type: str          # "BAZAAR", "NPC", "AH", "MAYOR"
    item_id: str
    item_name: str
    profit: float
    action: str        # "JETZT KAUFEN" or "JETZT INVESTIEREN"
    details: dict
    confidence: str    # "high", "medium", "low"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
