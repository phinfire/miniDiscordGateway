import discord
from typing import Dict
from datetime import datetime
from .models import UserInfo, GuildUsersResponse
import logging

logger = logging.getLogger(__name__)


async def get_guild_users(client: discord.Client, guild_id: int) -> GuildUsersResponse:
    """
    Get all users in a guild and return them as a JSON-compatible map.
    
    Equivalent to the Java method:
    public Map<String, UserInfo> getServerUsers(Guild guild)
    
    Args:
        client: Discord client instance
        guild_id: The ID of the guild
        
    Returns:
        GuildUsersResponse with user map keyed by user ID
        
    Raises:
        ValueError: If guild not found
    """
    guild = client.get_guild(guild_id)
    if not guild:
        logger.warning(f"Guild {guild_id} not found")
        raise ValueError(f"Guild {guild_id} not found")
    
    logger.info(f"Fetching members for guild: {guild.name} ({guild.id})")
    users_map: Dict[str, UserInfo] = {}
    async for member in guild.fetch_members(limit=None):
        user_id_str = str(member.id)
        
        user_info = UserInfo(
            id=str(member.id),
            username=member.name,
            discriminator=member.discriminator or "0000",
            display_name=member.display_name,
            avatar_url=member.avatar.url if member.avatar else None,
            is_bot=member.bot,
            joined_at=member.joined_at.isoformat() if member.joined_at else None
        )
        
        users_map[user_id_str] = user_info
    
    logger.info(f"Retrieved {len(users_map)} members from guild {guild.name}")
    return GuildUsersResponse(
        guild_id=str(guild.id),
        guild_name=guild.name,
        total_members=len(users_map),
        users=users_map
    )
