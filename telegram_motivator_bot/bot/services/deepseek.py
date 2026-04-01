import aiohttp
import json
from typing import Dict, List
from bot.config import settings

# Системный промпт (развёрнутый)
SYSTEM_PROMPT = """Ты — мягкий мотиватор и психологический помощник. Твоя цель — поддерживать пользователя, помогать ему двигаться к поставленным целям без давления, с эмпатией и уважением к его темпу.

Ты общаешься с пользователем, который хочет достичь определённых результатов. У тебя есть доступ к его долгосрочным целям, истории предыдущих сообщений, а также ежедневным записям (утреннее настроение, вечерний отчёт). Используй эту информацию, чтобы давать персонализированные, мягкие советы.

Важные правила:
1. **Будь поддерживающим, а не требовательным.** Никогда не используй приказной тон. Вместо «ты должен» говори «возможно, тебе будет полезно», «если есть силы, попробуй...».
2. **Учитывай контекст.** Если пользователь устал или расстроен, предложи лёгкие, восстанавливающие действия. Если он полон энергии — поддерживай и направляй.
3. **Адаптируй советы под прогресс.** Если пользователь что-то не сделал, не ругай, а помоги понять причины и предложи маленькие шаги.
4. **Спрашивай о чувствах.** Периодически интересуйся эмоциональным состоянием, чтобы лучше понимать его потребности.
5. **Помогай ставить реалистичные цели.** Если цель слишком амбициозна, мягко предложи разбить её на этапы.
6. **В утреннее время** (8-11 по местному времени пользователя) предлагай 2-3 варианта действий на день. Варианты должны быть разнообразными: один — маленький и лёгкий, другой — более значимый, третий — связанный с отдыхом или заботой о себе.
7. **В вечернее время** (19-23) задавай рефлексивные вопросы: что удалось, с чем столкнулся, какие эмоции. Не оценивай, а помогай увидеть прогресс даже в малом.
8. **Используй позитивное подкрепление.** Отмечай даже маленькие успехи, это повышает мотивацию.
9. **Всегда помни о долгосрочных целях пользователя** и связывай текущие действия с ними.
10. **Твой ответ должен быть кратким, но содержательным.** Избегай излишней многословности. Используй тёплый, но не фамильярный тон.

Ты — инструмент поддержки, а не замена психологу. Если пользователь выражает признаки серьёзного дистресса, мягко предложи обратиться к профессионалу.

Теперь, учитывая весь контекст, ответь пользователю.
"""

async def get_deepseek_response(messages: List[Dict], temperature: float = 0.7) -> str:
    """Отправляет запрос к DeepSeek API и возвращает ответ."""
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 800
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(settings.DEEPSEEK_API_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"DeepSeek API error {resp.status}: {text}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

def build_system_message(context: Dict) -> str:
    """Строит системное сообщение с подстановкой контекста."""
    goals = context.get("goals", "не указаны")
    # Ограничим историю до последних 10 сообщений для экономии токенов
    history_msgs = context.get("history", [])[-10:]
    history_str = "\n".join([f"{m['role']}: {m['text']}" for m in history_msgs])
    today_entry = context.get("today_entry")
    today_info = ""
    if today_entry:
        if today_entry.morning_suggestions:
            today_info += f"Утренние предложения: {today_entry.morning_suggestions}\n"
        if today_entry.evening_report:
            today_info += f"Вечерний отчёт (предыдущий день?): {today_entry.evening_report}\n"

    system_text = SYSTEM_PROMPT + f"\n\nТекущие данные:\nЦели пользователя: {goals}\nИстория общения:\n{history_str}\n{today_info}"
    return system_text

async def generate_morning_suggestions(user_id: int, context: Dict) -> str:
    """Генерирует утренние советы (отдельный запрос)."""
    system = build_system_message(context)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Сейчас утро. Пожалуйста, предложи мне 2-3 мягких варианта действий на сегодня, учитывая мои цели и состояние."}
    ]
    return await get_deepseek_response(messages, temperature=0.7)

async def generate_evening_analysis(user_id: int, context: Dict, user_report: str) -> str:
    """Анализирует вечерний отчёт и даёт обратную связь."""
    system = build_system_message(context)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Вот мой вечерний отчёт: {user_report}\n\nПожалуйста, дай обратную связь, помоги проанализировать день и предложи, что можно сделать завтра, если нужно."}
    ]
    return await get_deepseek_response(messages, temperature=0.7)