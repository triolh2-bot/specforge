import os
import secrets

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    PORT = int(os.environ.get("PORT", 5000))

    MINIMAX_CLIENT_ID = os.environ.get("MINIMAX_CLIENT_ID", "")
    MINIMAX_CLIENT_SECRET = os.environ.get("MINIMAX_CLIENT_SECRET", "")
    MINIMAX_REDIRECT_URI = os.environ.get("MINIMAX_REDIRECT_URI", "")
    MINIMAX_AUTH_URL = "https://platform.minimaxi.com/oauth/authorize"
    MINIMAX_TOKEN_URL = "https://platform.minimaxi.com/oauth/token"
    MINIMAX_API_BASE = "https://api.minimaxi.com/v1"

    MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")
    MINIMAX_CHAT_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    MINIMAX_MODEL = "MiniMax-M2.5"
