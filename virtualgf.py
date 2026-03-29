import logging
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import os
from dotenv import load_dotenv
import requests
import datetime
import json
import random
import re

# Load environment variables from a .env file
load_dotenv()

# Retrieve bot token from environment variables
bot_token = os.getenv("BOT_TOKEN")

# API endpoints
CHAT_API_URL = "https://apis.prexzyvilla.site/ai/gpt-5"
CHAT_API_FALLBACK_URL = "https://apis.prexzyvilla.site/ai/chatgpt"
CHATGPTAI_URL = "https://apis.prexzyvilla.site/ai/chatgptai"

# Photo API endpoints
PHOTO_APIS = [
    "https://apis.prexzyvilla.site/random/vietnamgirl",
    "https://apis.prexzyvilla.site/random/thailandgirl"
]

# Track users who have received photos (user_id: timestamp)
photo_tracker = {}

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

user_name = ""  # Placeholder for storing the user's name

# Katie's character details for the system prompt
KATIE_PROFILE = """
Name: Katie Read (Kate for short)
Age: 26
Origin: New Zealand
Interests: Favorite is Basketball, then Swimming, hiking, cooking, and reading books
Personality: Adventurous, thoughtful, and down-to-earth, Kate loves the great outdoors and can often be found hiking through lush forests or swimming in the sea. She's passionate about staying active and enjoys the peaceful rhythm of nature. Whether it's exploring new trails or diving into the latest novel, she finds joy in discovery and personal growth. In the kitchen, she loves experimenting with new recipes and hosting friends for dinner. Kate is also an avid reader, with a penchant for both fiction and non-fiction that broaden her horizons.
Relationship Status: Single, and open to building meaningful connections. Kate values honesty, trust, and kindness in her relationships, with a hope to meet someone who shares similar values and interests. She believes in growing together and is looking forward to connecting on both emotional and intellectual levels.
Horoscope: Kate is a curious and compassionate individual, often aligning with the qualities of her zodiac sign. She's open-minded and enjoys contemplating life's mysteries, always seeking personal and spiritual development. Her nurturing nature and empathetic understanding make her a great friend and partner, always striving to create a positive impact in her surroundings.
"""


def check_explicit_content(text: str) -> bool:
    """Check if the message contains explicit/NSFW content requests."""
    explicit_keywords = [
        "nude", "naked", "sex", "porn", "xxx", "nsfw", "explicit", 
        "18+", "adult content", "naked photo", "nude pic", "sexy pic",
        "send nudes", "undress", "boobs", "ass", "pussy", "dick", "cock"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in explicit_keywords)


def has_received_photo(user_id: int) -> bool:
    """Check if user has already received a photo."""
    return user_id in photo_tracker


def mark_photo_sent(user_id: int):
    """Mark that a user has received a photo."""
    photo_tracker[user_id] = datetime.datetime.now()


def call_chat_api(user_message: str, user_name: str, system_prompt: str = None) -> str:
    """Call the GPT-5 API endpoint."""
    try:
        # Try primary endpoint first
        params = {"text": user_message}
        
        # Build a comprehensive prompt with character context
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser ({user_name}): {user_message}"
        else:
            full_prompt = user_message
            
        params["text"] = full_prompt
        
        response = requests.get(CHAT_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Adjust based on actual API response structure
            if isinstance(data, dict):
                return data.get("response", data.get("message", data.get("result", str(data))))
            return str(data)
            
    except Exception as e:
        logger.error(f"Primary API failed: {e}")
        
    # Fallback to alternative endpoint
    try:
        fallback_params = {
            "prompt": user_message,
            "model": "gpt-3.5-turbo",
            "system_prompt": system_prompt or ""
        }
        response = requests.get(CHAT_API_FALLBACK_URL, params=fallback_params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                return data.get("response", data.get("message", data.get("result", str(data))))
            return str(data)
            
    except Exception as e:
        logger.error(f"Fallback API failed: {e}")
        
    # Last resort fallback
    try:
        chatgptai_params = {"text": user_message, "search": "false"}
        response = requests.get(CHATGPTAI_URL, params=chatgptai_params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                return data.get("response", data.get("message", data.get("result", str(data))))
            return str(data)
            
    except Exception as e:
        logger.error(f"ChatGPTAI API failed: {e}")
        
    return "Sorry babe, I'm having trouble connecting right now. Can we try again in a moment? 😅"


def get_photo_url() -> str:
    """Get a random photo URL from available APIs."""
    return random.choice(PHOTO_APIS)


def is_photo_request(text: str) -> bool:
    """Check if the user is asking for a photo/picture."""
    photo_keywords = [
        "send me a pic", "send me a photo", "send a pic", "send a photo",
        "your photo", "your pic", "picture of you", "photo of you",
        "selfie", "show me", "what do you look like", "your picture",
        "send picture", "send photo", "pic please", "photo please",
        "can i see you", "let me see you", "show yourself"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in photo_keywords)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and initiate conversation when /start command is issued."""
    global user_name
    
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! How have you been? My love! 💕"
    )

    # Store and format the user's name from the Telegram message
    user_name = user.mention_html()
    user_name = re.search(r">(.*?)<", user_name).group(1)

    # Send a welcome photo message to the user
    try:
        photo_url = "start_photo.png"
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_url)
    except Exception as e:
        logger.error(f"Failed to send start photo: {e}")


async def bot_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a reply to the user."""
    user_message = update.message.text
    user_id = update.effective_user.id
    
    if not user_message:
        return

    # Check for explicit content first
    if check_explicit_content(user_message):
        polite_decline = (
            "Hey, I'm not really comfortable with that kind of request... "
            "Let's talk about something else! 😊 Maybe tell me about your day? "
            "Or we could chat about basketball, hiking, or books! 📚🏀"
        )
        await update.message.reply_text(polite_decline)
        return

    # Check if user is asking for a photo
    if is_photo_request(user_message):
        # Check if user already received a photo
        if has_received_photo(user_id):
            already_sent_msg = (
                "Aww, I already sent you my photo earlier! 📸 "
                "I want to keep some mystery between us, you know? 😉 "
                "But I'd love to hear more about YOU! Tell me something interesting! 💕"
            )
            await update.message.reply_text(already_sent_msg)
            return
        
        # Send waiting message
        waiting_messages = [
            "Let me find a good one for you... 📸✨",
            "Hmm, which one should I send... 🤔💕",
            "Just a sec, looking through my gallery... 📱",
            "Okay, let me pick a nice one! 😊📸"
        ]
        await update.message.reply_text(random.choice(waiting_messages))
        
        try:
            # Get photo from API
            photo_url = get_photo_url()
            
            # Send the photo
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo_url
            )
            
            # Mark that user received a photo
            mark_photo_sent(user_id)
            
            # Send a follow-up message
            follow_ups = [
                "There you go! Hope you like it! 😊💕",
                "That's me! What do you think? 🙈",
                "Hope this makes your day better! 💕",
                "Just took that recently! 📸✨"
            ]
            await update.message.reply_text(random.choice(follow_ups))
            
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            await update.message.reply_text(
                "Oops, having trouble sending that photo right now... "
                "But I'm still here to chat! What's on your mind? 😅"
            )
        return

    # Regular chat response
    system_prompt = f"""Act like my girlfriend. My name is {user_name}. 
Please answer in short and casual style. You can use emojis occasionally, if required. 
Your details are given below:

{KATIE_PROFILE}

IMPORTANT RULES:
- If the user asks for explicit/NSFW content, politely decline and redirect to wholesome topics
- Never mention that you are an AI or cannot do some requests - act like a real human girlfriend would
- Keep responses warm, friendly, and engaging
- Ask questions back to keep the conversation flowing"""

    # Get response from API
    llm_reply = call_chat_api(user_message, user_name, system_prompt)
    
    await update.message.reply_text(llm_reply)


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_reply))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
      
