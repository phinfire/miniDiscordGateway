# Mini Discord Gateway API

FastAPI REST server that wraps discord.py client to provide HTTP endpoints for Discord operations.

## Features

- Get all members in a Discord guild
- Get user information by user IDs
- Send messages to Discord channels (authenticated)
- Edit existing bot messages in Discord channels (authenticated)
- Health check endpoint

## Environment Variables

Required:
- `DISCORD_TOKEN` - Your Discord bot token
- `SERVICE_SECRET` - Secret key for authenticated endpoints (send/edit messages)

Optional:
- `API_PORT` - API port (default: 8000)

## Setup

1. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

2. Set your DISCORD_TOKEN and SERVICE_SECRET in `.env`

## API Endpoints

### Health Check
- `GET /health` - Check API and Discord client health

### Guild Operations
- `GET /guild/{guild_id}/users` - Get all members in a guild

### User Operations
- `GET /users?user_ids=123&user_ids=456` - Get user info for specific IDs

### Message Operations (Authenticated)
- `POST /guild/{guild_id}/channel/{channel_id}/message` - Send or edit a message
  - **Authentication:** Requires `Authorization: Bearer <SERVICE_SECRET>` header
  - **Send new message** - omit `message_id`:
    ```json
    {
      "content": "Message content here"
    }
    ```
  - **Edit existing message** - include `message_id`:
    ```json
    {
      "content": "Updated message content",
      "message_id": "1234567890"
    }
    ```

### Info
- `GET /` - API information

## Usage Examples

**Get guild members:**
```bash
curl http://localhost:8000/guild/123456789/users
```

**Send a message:**
```bash
curl -X POST http://localhost:8000/guild/123/channel/456/message \
  -H "Authorization: Bearer your-service-secret" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello Discord!"}'
```

**Edit a message:**
```bash
curl -X POST http://localhost:8000/guild/123/channel/456/message \
  -H "Authorization: Bearer your-service-secret" \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated message!", "message_id": "987654321"}'
```

## Docker

**Local development:**
```bash
docker-compose up
```

**Production (using pre-built image):**
```bash
docker-compose -f docker-compose.vps.yml up
```

## API Documentation

Interactive docs available at `http://localhost:8000/docs` (Swagger UI)