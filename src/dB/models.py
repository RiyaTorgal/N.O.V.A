from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

@dataclass
class CommandEntry:
    history_id: int
    command: str
    timestamp: datetime
    execution_status: str
    response: Optional[str] = None
    context: Optional[Dict] = None

@dataclass
class Category:
    id: int
    name: str
    description: Optional[str] = None

@dataclass
class Tag:
    id: int
    name: str

@dataclass
class Note:
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    is_pinned: bool = False
    is_archived: bool = False
    category_id: Optional[int] = None
    tags: Optional[List[Tag]] = None

@dataclass
class NoteTag:
    note_id: int
    tag_id: int