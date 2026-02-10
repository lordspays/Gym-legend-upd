from bot.utils import format_number
from vkbottle.bot import BotLabeler, Message

from bot.core.config import settings
from bot.db import (
    create_player,
    get_player,
    get_top_balance,
    get_top_lifts,
    get_top_fitness_halls,
)

top_labeler = BotLabeler()
top_labeler.vbml_ignore_case = True


@top_labeler.message(text=["топ", "/топ"])
async def get_top_list_handler(message: Message):
    """Список топов"""
    user_id = message.from_id
    player = await get_player(user_id)

    if not player:
        player = await create_player(user_id, str(message.from_id))

    top_text = (
        "🏆 Система рейтинга - 𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃\n\n"
        "📊 Доступные команды рейтинга:\n\n"
        "💲 Топ монет - топ игроков по балансу\n"
        "💪 Топ поднятий - топ по количеству поднятий\n"
        "🏰 К топ - топ кланов\n"
        "🏦 Топ фитнесс залов - топ по количеству фитнесс залов.\n\n"
        " Ваши показатели:\n"
        f"💰 Баланс: {format_number(player['balance'])} монет\n"
        f"🦾 Поднятий: {format_number(player['total_lifts'])}\n"
        f"⚖️ Гантеля: {player['dumbbell_name']}\n\n"
        "Выберите нужный рейтинг из списка выше!"
    )

    return top_text


@top_labeler.message(text=["топ монет", "/топ монет"])
async def get_top_balance_handler(message: Message):
    """Топ по монетам"""
    top_players = await get_top_balance(10)

    if not top_players:
        return "🏆 Рейтинг пока пуст. Будьте первым!"

    top_text = "🏆 Рейтинг по монетам:\n\n"

    for i, (user_id, username, balance, dumbbell_name) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        top_text += f"{medal} {i}. [id{user_id}|{username}] - {format_number(balance)} монет\n\n"

    await message.answer(top_text, disable_mentions=True)


@top_labeler.message(text=["топ поднятий", "/топ поднятий"])
async def get_top_lifts_handler(message: Message):
    """Топ по поднятиям"""
    top_players = await get_top_lifts(10)

    if not top_players:
        return "🏆 Рейтинг пока пуст. Будьте первым!"

    top_text = "💪 Рейтинг по поднятиям:\n\n"

    for i, (user_id, username, total_lifts, dumbbell_name) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        top_text += f"{medal} {i}. [id{user_id}|{username}] - {format_number(total_lifts)} поднятий 💪\n\n"

    await message.answer(top_text, disable_mentions=True)


@top_labeler.message(text=["топ фитнесс залов", "/топ фитнесс залов"])
async def get_top_fitness_halls_handler(message: Message):
    """Топ по фитнесс залам"""
    top_players = await get_top_fitness_halls(10)

    if not top_players:
        return "🏆 Рейтинг пока пуст. Будьте первым!"

    top_text = "🏦 Рейтинг по фитнесс залам:\n\n"

    for i, (user_id, username, fitness_halls, dumbbell_name) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        top_text += f"{medal} {i}. [id{user_id}|{username}]\n"
        top_text += f"   🏦 {format_number(fitness_halls)} фитнесс залов\n\n"

    await message.answer(top_text, disable_mentions=True)
