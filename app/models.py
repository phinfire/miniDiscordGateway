from pydantic import BaseModel
from typing import Dict, Any

class UserInfo(BaseModel):
    """Discord user information."""
    id: str
    username: str
    discriminator: str | None
    display_name: str | None
    avatar_url: str | None
    is_bot: bool
    joined_at: str | None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 123456789,
                "username": "user#0001",
                "discriminator": "0001",
                "display_name": "User Display Name",
                "avatar_url": "https://cdn.discordapp.com/...",
                "is_bot": False,
                "joined_at": "2023-01-15T10:30:00Z"
            }
        }


class GuildUsersResponse(BaseModel):
    """Response containing user map for a guild."""
    guild_id: str
    guild_name: str
    total_members: int
    users: Dict[str, UserInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "guild_id": 987654321,
                "guild_name": "My Server",
                "total_members": 42,
                "users": {
                    "123456789": {
                        "id": 123456789,
                        "username": "user#0001",
                        "discriminator": "0001",
                        "display_name": "User",
                        "avatar_url": "https://cdn.discordapp.com/...",
                        "is_bot": False,
                        "joined_at": "2023-01-15T10:30:00Z"
                    }
                }
            }
        }


class UsersResponse(BaseModel):
    """Response containing user info for multiple user IDs."""
    total_found: int
    users: Dict[str, UserInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "total_found": 2,
                "users": {
                    "123456789": {
                        "id": 123456789,
                        "username": "user1",
                        "discriminator": "0001",
                        "display_name": "User One",
                        "avatar_url": "https://cdn.discordapp.com/...",
                        "is_bot": False,
                        "joined_at": "2023-01-15T10:30:00Z"
                    },
                    "987654321": {
                        "id": 987654321,
                        "username": "user2",
                        "discriminator": "0002",
                        "display_name": "User Two",
                        "avatar_url": "https://cdn.discordapp.com/...",
                        "is_bot": True,
                        "joined_at": "2023-02-20T15:45:00Z"
                    }
                }
            }
        }


class UserIdsRequest(BaseModel):
    """Request model for fetching users by IDs."""
    user_ids: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": ["123456789", "987654321"]
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Guild not found",
                "detail": "Guild ID 999 does not exist"
            }
        }
