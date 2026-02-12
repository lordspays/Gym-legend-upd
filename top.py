from bot.utils import format_number
from vkbottle.bot import BotLabeler, Message

from bot.core.config import settings
from bot.db import (
    create_player,
    get_player,
    get_top_balance,
    get_top_lifts,
    get_top_fitness_halls,
    get_top_power,
)

top_labeler = BotLabeler()
top_labeler.vbml_ignore_case = True


def get_equipment_type(level: int) -> dict:
    """Возвращает информацию о типе снаряда в зависимости от уровня"""
    if level <= 10:
        return {
            "name": "Гантеля",
            "emoji": "🏋️",
            "possessive": "Гантеля"
        }
    elif 11 <= level <= 15:
        return {
            "name": "Штанга",
            "emoji": "🏋️",
            "possessive": "Штанга"
        }
    else:
        return {
            "name": "Становая тяга",
            "emoji": "🏋️",
            "possessive": "Вес на становой тяге"
        }


@top_labeler.message(text=["топ", "/топ"])
async def get_top_list_handler(message: Message):
    """Список топов"""
    user_id = message.from_id
    player = await get_player(user_id)

    if not player:
        player = await create_player(user_id, str(message.from_id))
    
    equipment_type = get_equipment_type(player["dumbbell_level"])

    top_text = (
        "🏆 Система рейтинга - 𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃\n\n"
        "📊 Доступные команды рейтинга:\n\n"
        "💲 Топ монет - топ игроков по балансу\n"
        "💪 Топ поднятий - топ по количеству поднятий\n"
        "💪 Топ силы - топ игроков по силе\n"
        "🏰 К топ - топ кланов\n"
        "🏦 Топ фитнесс залов - топ по количеству фитнесс залов.\n\n"
        " Ваши показатели:\n"
        f"💰 Баланс: {format_number(player['balance'])} монет\n"
        f"🦾 Поднятий: {format_number(player['total_lifts'])}\n"
        f"⚖️ Сила: {format_number(player['power'])}\n"
        f"🎮 {equipment_type['possessive']}: {player['dumbbell_name']} (Ур. {player['dumbbell_level']})\n\n"
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

    for i, (user_id, username, balance, dumbbell_name, dumbbell_level) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        equipment_type = get_equipment_type(dumbbell_level)
        top_text += f"{medal} {i}. [id{user_id}|{username}]\n"
        top_text += f"   💰 {format_number(balance)} монет\n"
        top_text += f"   🎮 {equipment_type['possessive']}: {dumbbell_name} (Ур. {dumbbell_level})\n\n"

    await message.answer(top_text, disable_mentions=True)


@top_labeler.message(text=["топ поднятий", "/топ поднятий"])
async def get_top_lifts_handler(message: Message):
    """Топ по поднятиям"""
    top_players = await get_top_lifts(10)

    if not top_players:
        return "🏆 Рейтинг пока пуст. Будьте первым!"

    top_text = "💪 Рейтинг по поднятиям:\n\n"

    for i, (user_id, username, total_lifts, dumbbell_name, dumbbell_level) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        equipment_type = get_equipment_type(dumbbell_level)
        top_text += f"{medal} {i}. [id{user_id}|{username}]\n"
        top_text += f"   🦾 {format_number(total_lifts)} поднятий\n"
        top_text += f"   🎮 {equipment_type['possessive']}: {dumbbell_name} (Ур. {dumbbell_level})\n\n"

    await message.answer(top_text, disable_mentions=True)


@top_labeler.message(text=["топ силы", "/топ силы"])
async def get_top_power_handler(message: Message):
    """Топ по силе"""
    top_players = await get_top_power(10)

    if not top_players:
        return "🏆 Рейтинг пока пуст. Будьте первым!"

    top_text = "💪 Рейтинг по силе:\n\n"

    for i, (user_id, username, power, dumbbell_name, dumbbell_level) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        equipment_type = get_equipment_type(dumbbell_level)
        top_text += f"{medal} {i}. [id{user_id}|{username}]\n"
        top_text += f"   💪 Сила: {format_number(power)}\n"
        top_text += f"   🎮 {equipment_type['possessive']}: {dumbbell_name} (Ур. {dumbbell_level})\n\n"

    await message.answer(top_text, disable_mentions=True)


@top_labeler.message(text=["топ фитнесс залов", "/топ фитнесс залов"])
async def get_top_fitness_halls_handler(message: Message):
    """Топ по фитнесс залам"""
    top_players = await get_top_fitness_halls(10)

    if not top_players:
        return "🏆 Рейтинг пока пуст. Будьте первым!"

    top_text = "🏦 Рейтинг по фитнесс залам:\n\n"

    for i, (user_id, username, fitness_halls, dumbbell_name, dumbbell_level) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        equipment_type = get_equipment_type(dumbbell_level)
        top_text += f"{medal} {i}. [id{user_id}|{username}]\n"
        top_text += f"   🏦 {format_number(fitness_halls)} фитнесс залов\n"
        top_text += f"   🎮 {equipment_type['possessive']}: {dumbbell_name} (Ур. {dumbbell_level})\n\n"

    await message.answer(top_text, disable_mentions=True)
