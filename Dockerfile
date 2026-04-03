FROM python:3.11-slim

WORKDIR /app

# Копируем только requirements сначала для кэширования слоя
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY bot/ ./bot/

# Переменные окружения будут переданы через -e или docker-compose
# (не встраиваем их в образ)

EXPOSE 8080

# Запуск бота как модуля
CMD ["python", "-m", "bot.main"]
