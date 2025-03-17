from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

@dataclass
class User:
    user_id: int
    username: str
    email: str
    password_hash: str
    created_at: datetime
    registration_date: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

@dataclass
class CommandEntry:
    history_id: int
    user_id: int
    command: str
    timestamp: datetime
    execution_status: str
    context: Optional[Dict] = None

# @dataclass
# class Session:
#     id: str
#     user_id: int
#     session_token: str
#     created_at: datetime
#     expires_at: datetime

# @dataclass
# class PasswordReset:
#     id: str
#     user_id: int
#     reset_token: str
#     requested_at: datetime
#     expires_at: datetime

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
    user_id: int
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