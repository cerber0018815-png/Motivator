from aiogram import Router, types
from aiogram.filters import Command
from bot.services.statistics import get_weekly_stats

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    stats = await get_weekly_stats(message.from_user.id)
    await message.answer(stats, parse_mode="Markdown")