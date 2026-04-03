# config.py — переменные окружения и настройки бота

import os

# Токен Telegram бота (получается у @BotFather)
TOKEN = os.getenv("BOT_TOKEN")

# Строка подключения к PostgreSQL (например: postgresql://user:pass@host/dbname)
DATABASE_URL = os.getenv("DATABASE_URL")

# API ключ DeepSeek (получается на platform.deepseek.com)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Базовый URL API DeepSeek
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Список Telegram ID администраторов (целые числа)
ADMINS = [928589977]  # замените на свой ID
