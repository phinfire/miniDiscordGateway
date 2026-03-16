"""
FastAPI REST Server for Discord Guild User Retrieval
Wraps discord.py client with async HTTP endpoints
"""
import os
import asyncio
import logging
import time
import discord
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from .discord_client import DiscordClientManager
from .services import get_guild_users, get_users_by_ids, send_message
from .models import GuildUsersResponse, UsersResponse, ErrorResponse, SendMessageRequest, SendMessageResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set")

SERVICE_SECRET = os.getenv("SERVICE_SECRET")
if not SERVICE_SECRET:
    raise ValueError("SERVICE_SECRET environment variable not set")

client = DiscordClientManager.get_client(DISCORD_TOKEN)
client_ready = asyncio.Event()
app_start_time = None


async def verify_api_key(authorization: str = Header(...)) -> bool:
    """
    Verify API key for protected endpoints.
    Expected header format: Authorization: Bearer <service_secret>
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        scheme, credentials = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if credentials != SERVICE_SECRET:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True

@client.event
async def on_ready():
    """Called when Discord client is ready."""
    logger.info(f"✅ Discord bot ready as {client.user}")
    client_ready.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup and shutdown of Discord client.
    """
    global app_start_time
    logger.info("🚀 Starting Discord client...")
    
    async def run_discord_client():
        try:
            await DiscordClientManager.start(DISCORD_TOKEN)
        except Exception as e:
            logger.error(f"Discord client error: {e}")
    
    discord_task = asyncio.create_task(run_discord_client())
    try:
        await asyncio.wait_for(client_ready.wait(), timeout=10.0)
        logger.info("Discord client is ready")
        app_start_time = time.time()
    except asyncio.TimeoutError:
        logger.error("Discord client failed to initialize within timeout")
        discord_task.cancel()
        raise
    
    yield
    logger.info("🛑 Shutting down Discord client...")
    await DiscordClientManager.close()
    discord_task.cancel()
    try:
        await discord_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Mini Discord Gateway API",
    description="REST API to retrieve Discord guild users",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Check API and Discord client health."""
    uptime_seconds = time.time() - app_start_time if app_start_time else None
    return {
        "status": "ok",
        "discord_client_ready": client.is_ready(),
        "discord_bot_name": str(client.user) if client.user else "Not connected",
        "uptime_seconds": uptime_seconds
    }


@app.get("/guild/{guild_id}/users", response_model=GuildUsersResponse, tags=["Guild Operations"])
async def get_guild_users_endpoint(guild_id: int) -> GuildUsersResponse:
    """Get all users in a Discord guild."""
    if guild_id <= 0:
        raise HTTPException(status_code=400, detail="Guild ID must be positive")
    
    if not client.is_ready():
        logger.error("Discord client is not ready")
        raise HTTPException(status_code=503, detail="Discord client is not ready")
    
    try:
        return await get_guild_users(client, guild_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except discord.Forbidden:
        raise HTTPException(status_code=403, detail="Bot lacks permission")
    except discord.HTTPException as e:
        logger.error(f"Discord API error: {e}")
        raise HTTPException(status_code=502, detail="Discord API error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error")


@app.get("/users", response_model=UsersResponse, tags=["User Operations"])
async def get_users_by_ids_endpoint(user_ids: list[str] = Query(...)) -> UsersResponse:
    """Get user info for a list of user IDs (query params: ?user_ids=123&user_ids=456)"""
    if not user_ids:
        raise HTTPException(status_code=400, detail="user_ids list cannot be empty")
    
    if not client.is_ready():
        logger.error("Discord client is not ready")
        raise HTTPException(status_code=503, detail="Discord client is not ready")
    
    try:
        return await get_users_by_ids(client, user_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except discord.HTTPException as e:
        logger.error(f"Discord API error: {e}")
        raise HTTPException(status_code=502, detail="Discord API error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error")


@app.post("/guild/{guild_id}/channel/{channel_id}/message", response_model=SendMessageResponse, tags=["Message Operations"])
async def send_message_endpoint(guild_id: int, channel_id: int, message: SendMessageRequest, _: bool = Depends(verify_api_key)) -> SendMessageResponse:
    """Send a message to a Discord channel. Requires valid API key in Authorization header."""
    if guild_id <= 0:
        raise HTTPException(status_code=400, detail="Guild ID must be positive")
    
    if channel_id <= 0:
        raise HTTPException(status_code=400, detail="Channel ID must be positive")
    
    if not client.is_ready():
        logger.error("Discord client is not ready")
        raise HTTPException(status_code=503, detail="Discord client is not ready")
    
    try:
        logger.info(f"Processing message request to guild {guild_id}, channel {channel_id}, message_id={message.message_id}")
        return await send_message(client, guild_id, channel_id, message.content, message.message_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except discord.Forbidden:
        raise HTTPException(status_code=403, detail="Bot lacks permission to send/edit messages in this channel")
    except discord.HTTPException as e:
        logger.error(f"Discord API error: {e}")
        raise HTTPException(status_code=502, detail="Discord API error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error")


@app.get("/", tags=["Info"])
async def root():
    """API information and status."""
    return {
        "name": "Mini Discord Gateway API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
