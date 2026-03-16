import asyncio
import discord
from typing import Dict
from .models import UserInfo, GuildUsersResponse, UsersResponse, SendMessageResponse
import logging

logger = logging.getLogger(__name__)

_user_cache: Dict[str, UserInfo] = {}
_cache_lock = asyncio.Lock()

_request_semaphore = asyncio.Semaphore(5)


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
            discriminator=member.discriminator,
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


async def get_users_by_ids(client: discord.Client, user_ids: list[str]) -> UsersResponse:
    """Get user information for a list of user IDs (fetched concurrently with caching)."""
    if not user_ids:
        raise ValueError("user_ids list cannot be empty")
    
    logger.info(f"Fetching {len(user_ids)} users")
    
    users_map: Dict[str, UserInfo] = {}
    uncached_ids = []
    
    async with _cache_lock:
        for uid in user_ids:
            if uid in _user_cache:
                users_map[uid] = _user_cache[uid]
            else:
                uncached_ids.append(uid)
    
    logger.info(f"Cache hit: {len(users_map)}, needs fetch: {len(uncached_ids)}")
    
    async def fetch_user_safe(user_id_str: str) -> tuple[str, UserInfo | None]:
        async with _request_semaphore:
            try:
                user_id = int(user_id_str)
                user = await client.fetch_user(user_id)
                user_info = UserInfo(
                    id=str(user.id),
                    username=user.name,
                    discriminator=user.discriminator,
                    display_name=user.display_name,
                    avatar_url=user.avatar.url if user.avatar else None,
                    is_bot=user.bot,
                    joined_at=None
                )
                return user_id_str, user_info
            except ValueError:
                logger.warning(f"Invalid user ID format: {user_id_str}")
            except discord.NotFound:
                logger.warning(f"User {user_id_str} not found")
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(f"Error fetching user {user_id_str}: {e}")
            return user_id_str, None

    if uncached_ids:
        results = await asyncio.gather(*[fetch_user_safe(uid) for uid in uncached_ids])
        
        async with _cache_lock:
            for uid, info in results:
                if info is not None:
                    _user_cache[uid] = info
                    users_map[uid] = info
    
    logger.info(f"Retrieved {len(users_map)} out of {len(user_ids)} users")
    return UsersResponse(total_found=len(users_map), users=users_map)


async def send_message(client: discord.Client, guild_id: int, channel_id: int, content: str, message_id: str | None = None) -> SendMessageResponse:
    """
    Send a new message or edit an existing message in a Discord channel.
    
    Args:
        client: Discord client instance
        guild_id: The ID of the guild
        channel_id: The ID of the channel
        content: The message content to send or edit
        message_id: Optional ID of an existing message to edit. If provided, edits instead of sending.
        
    Returns:
        SendMessageResponse with message details
        
    Raises:
        ValueError: If guild, channel, or message not found
        discord.Forbidden: If bot lacks permission to send/edit messages
    """
    guild = client.get_guild(guild_id)
    if not guild:
        logger.warning(f"Guild {guild_id} not found")
        raise ValueError(f"Guild {guild_id} not found")
    
    channel = guild.get_channel(channel_id)
    if not channel:
        logger.warning(f"Channel {channel_id} not found in guild {guild_id}")
        raise ValueError(f"Channel {channel_id} not found in guild {guild_id}")
    
    if not isinstance(channel, discord.TextChannel):
        logger.warning(f"Channel {channel_id} is not a text channel")
        raise ValueError(f"Channel {channel_id} is not a text channel")
    
    if not content or not content.strip():
        raise ValueError("Message content cannot be empty")
    
    try:
        if message_id:
            # Edit existing message
            logger.info(f"Fetching message {message_id} from channel {channel.name} ({channel_id}) in guild {guild.name}")
            try:
                message = await channel.fetch_message(int(message_id))
            except ValueError:
                raise ValueError(f"Invalid message ID format: {message_id}")
            except discord.NotFound:
                raise ValueError(f"Message {message_id} not found in channel {channel_id}")
            
            # Verify the message was sent by the bot
            if message.author != client.user:
                logger.warning(f"Message {message_id} was not sent by the bot (author: {message.author})")
                raise ValueError(f"Message {message_id} was not sent by the bot")
            
            logger.info(f"Editing message {message_id} in channel {channel.name}")
            await message.edit(content=content)
            logger.info(f"Message {message_id} edited successfully")
        else:
            # Send new message
            logger.info(f"Sending message to channel {channel.name} ({channel_id}) in guild {guild.name}")
            message = await channel.send(content)
            logger.info(f"Message sent successfully: {message.id}")
        
        return SendMessageResponse(
            message_id=str(message.id),
            guild_id=str(guild.id),
            channel_id=str(channel.id),
            author=str(message.author),
            content=message.content,
            timestamp=message.created_at.isoformat()
        )
    except discord.Forbidden as e:
        logger.error(f"Permission denied to send/edit message in channel {channel_id}: {e}")
        raise
    except discord.HTTPException as e:
        logger.error(f"Discord API error sending/editing message: {e}")
        raise
