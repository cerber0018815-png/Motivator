import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL")  # должно быть postgresql://...
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    MORNING_HOUR: int = 8
    EVENING_HOUR: int = 20

settings = Settings()