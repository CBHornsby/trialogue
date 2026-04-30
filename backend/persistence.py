"""
Debate persistence. Each debate is stored as a JSON file in ~/.debate-tool/debates/.
Survives restart, easy to inspect, easy to delete.
"""
import json
import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

DEBATES_DIR = Path.home() / ".debate-tool" / "debates"


@dataclass
class RoleResult:
    """The output and metadata from a single role's run."""
    text: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = "pending"  # pending | active | complete | error
    error_message: str = ""


@dataclass
class Debate:
    """Persistent debate state. Stored as JSON."""
    id: str
    question: str
    created_at: str
    updated_at: str
    status: str = "running"  # running | complete | error | stopped
    proposer: RoleResult = field(default_factory=RoleResult)
    critic: RoleResult = field(default_factory=RoleResult)
    judge: RoleResult = field(default_factory=RoleResult)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "proposer": asdict(self.proposer),
            "critic": asdict(self.critic),
            "judge": asdict(self.judge),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Debate":
        return cls(
            id=data["id"],
            question=data["question"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            status=data.get("status", "complete"),
            proposer=RoleResult(**data.get("proposer", {})),
            critic=RoleResult(**data.get("critic", {})),
            judge=RoleResult(**data.get("judge", {})),
        )

    def get_role(self, role: str) -> RoleResult:
        return getattr(self, role)

    def set_role(self, role: str, result: RoleResult) -> None:
        setattr(self, role, result)


def _ensure_dir() -> None:
    DEBATES_DIR.mkdir(parents=True, exist_ok=True)


def new_debate(question: str) -> Debate:
    """Create a new debate with a fresh UUID."""
    now = datetime.utcnow().isoformat()
    return Debate(
        id=str(uuid.uuid4()),
        question=question,
        created_at=now,
        updated_at=now,
    )


def save_debate(debate: Debate) -> None:
    """Persist debate to disk."""
    _ensure_dir()
    debate.updated_at = datetime.utcnow().isoformat()
    path = DEBATES_DIR / f"{debate.id}.json"
    with open(path, "w") as f:
        json.dump(debate.to_dict(), f, indent=2)


def load_debate(debate_id: str) -> Optional[Debate]:
    """Load a debate by ID, or None if not found."""
    path = DEBATES_DIR / f"{debate_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return Debate.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def list_recent_debates(limit: int = 50) -> List[Dict[str, Any]]:
    """List recent debates, most recent first. Returns metadata only, not full content."""
    _ensure_dir()
    debates = []
    for path in DEBATES_DIR.glob("*.json"):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            debates.append({
                "id": data["id"],
                "question": data["question"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "status": data.get("status", "complete"),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    debates.sort(key=lambda d: d["updated_at"], reverse=True)
    return debates[:limit]


def delete_debate(debate_id: str) -> bool:
    """Delete a debate by ID. Returns True if deleted, False if not found."""
    path = DEBATES_DIR / f"{debate_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
