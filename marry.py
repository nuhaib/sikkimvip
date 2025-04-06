import os
import asyncio
import logging
import pytz
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import ChatAdminRequiredError, FloodWaitError
from telethon.tl.types import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API credentials
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

# Ensure credentials are set
if not api_id or not api_hash:
    raise ValueError("Missing API credentials. Set TELEGRAM_API_ID and TELEGRAM_API_HASH as environment variables.")

api_id = int(api_id)  # Convert API ID to integer

# Source & Target Channels
source_channels = [-1002131606797]  # Replace with actual source channel(s)
target_channels = [-1002473646337, -1002297343613, -1002664314461]  # Replace with actual target channels

# Initialize Telegram client
client = TelegramClient('script4_session', api_id, api_hash, flood_sleep_threshold=10)

def is_allowed_time():
    """Check if the current time is outside the restricted time range (9:50 PM - 5:00 AM IST)."""
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)

    # Restricted time range
    start_restriction = now.replace(hour=21, minute=50, second=0, microsecond=0)  # 9:50 PM IST
    end_restriction = now.replace(hour=12, minute=0, second=0, microsecond=0)  # 12:00 PM IST

    # Handle overnight transition
    if start_restriction <= now or now < end_restriction:
        return False  # Block messages
    return True  # Allow forwarding

@client.on(events.NewMessage(chats=source_channels))
async def forward_messages(event):
    """Forward messages to target channels only during allowed times."""
    
    if not is_allowed_time():
        logger.info("Skipping message forwarding as it's between 9:50 PM and 12:00 PM IST.")
        return  # Stop processing further

    msg = event.message

    # Block GIFs (Documents with MIME type "video/mp4")
    if isinstance(msg.media, Document) and getattr(msg.media, "mime_type", "") == "video/mp4":
        logger.info("Skipping GIF message.")
        return

    text = msg.raw_text or ""  
    media = msg.media if msg.media else None
    entities = msg.entities  
    buttons = msg.reply_markup  

    tasks = [send_message(channel_id, text, media, entities, buttons) for channel_id in target_channels]
    await asyncio.gather(*tasks)

async def send_message(channel_id, text, media, entities, buttons):
    """Send messages while keeping formatting, media, and buttons intact."""
    try:
        await client.send_message(
            entity=channel_id,
            message=text,
            file=media,
            link_preview=True,
            buttons=buttons,
            formatting_entities=entities
        )
        logger.info(f"Message successfully forwarded to {channel_id}")
    except ChatAdminRequiredError:
        logger.error(f"Bot is not an admin in {channel_id}")
    except FloodWaitError as e:
        logger.warning(f"FloodWaitError: Sleeping for {e.seconds} seconds before retrying...")
        await asyncio.sleep(e.seconds)
        return await send_message(channel_id, text, media, entities, buttons)
    except Exception as e:
        logger.error(f"Failed to send message to {channel_id}: {e}")

async def main():
    """Start the Telegram client."""
    logger.info("Script 4 Forwarder is running...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
