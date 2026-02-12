from datetime import datetime
import re

from vkbottle.bot import BotLabeler, Message

from bot.core.config import settings
from bot.db import (
    create_player,
    get_player,
    get_player_clan,
    update_dumbbell_level,
    update_player_balance,
)
from bot.services.clans import (
    get_clan_bonuses,
    process_dumbbell_lift_with_clan,
)
from bot.utils import format_number

dumbbell_labeler = BotLabeler()
dumbbell_labeler.vbml_ignore_case = True


def get_equipment_type(level: int) -> dict:
    """Возвращает информацию о типе снаряда в зависимости от уровня"""
    if level <= 10:
        return {
            "name": "Гантеля",
            "action": "подняли гантелю",
            "possessive": "Ваша гантеля"
        }
    elif 11 <= level <= 15:
        return {
            "name": "Штанга",
            "action": "подняли штангу",
            "possessive": "Ваша штанга"
        }
    else:
        return {
            "name": "Вес на становой тяге",
            "action": "выполнили становую тягу",
            "possessive": "Ваш вес на становой тяге"
        }


@dumbbell_labeler.message(text=["гантеля", "/гантеля"])
async def get_dumbbell_info_handler(message: Message):
    """Информация о текущем снаряде"""
    user_id = message.from_id
    player = await get_player(user_id)

    equipment_type = get_equipment_type(player["dumbbell_level"])

    if player.get("custom_income") is not None:
        income_per_use = player["custom_income"]
        custom_note = f"⚡ Кастомный доход\n"
        dumbbell_info = {"power_per_use": 1}
    else:
        dumbbell_info = settings.DUMBBELL_LEVELS[player["dumbbell_level"]]
        income_per_use = dumbbell_info["income_per_use"]
        custom_note = ""

    next_level = player["dumbbell_level"] + 1

    if next_level in settings.DUMBBELL_LEVELS:
        next_dumbbell = settings.DUMBBELL_LEVELS[next_level]
        upgrade_info = f"🔜 Следующий уровень: \n{next_dumbbell['name']}\n💵 Цена: {format_number(next_dumbbell['price'])} монет\n💰 Доход за подход: {next_dumbbell['income_per_use']} монет"
    else:
        upgrade_info = "🏆 Вы достигли максимального уровня!"

    # Проверяем бонусы клана
    clan = await get_player_clan(user_id)
    income_text = ""
    if clan:
        clan_bonuses = get_clan_bonuses(clan["level"])
        income_text = f"💰 Доход за подход с бонусом клана: {income_per_use} + {clan_bonuses['lift_bonus_coins']} монет"
    else:
        income_text = f"💰 Доход за подход: {income_per_use} монет"

    info_text = (
        f"🤝 {equipment_type['possessive']}:\n\n"
        f"{custom_note}"
        f"⚖️ Вес: {player['dumbbell_name']}\n"
        f"{income_text}\n"
        f"💪 Сила за подход: {dumbbell_info['power_per_use']}\n\n"
        f"{upgrade_info}"
    )

    return info_text


@dumbbell_labeler.message(text=["поднять", "/поднять"])
async def use_dumbbell_handler(message: Message):
    """Поднять снаряд"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    equipment_type = get_equipment_type(player["dumbbell_level"])

    # Проверка кулдауна (уменьшен до 30 секунд)
    last_use_str = player['last_dumbbell_use']
    if last_use_str:
        last_use = datetime.fromisoformat(last_use_str)
        seconds_passed = (datetime.now() - last_use).total_seconds()

        if seconds_passed < 30:
            seconds_left = int(30 - seconds_passed)
            return f'⏳ Время отдыха! Подождите {seconds_left} секунд'

    # Обрабатываем поднятие с новой системой кланов
    income_calculation = await process_dumbbell_lift_with_clan(user_id)

    # Формируем сообщение
    clan = await get_player_clan(user_id)
    
    # Извлекаем только вес из названия снаряда
    dumbbell_name = player['dumbbell_name']
    weight_match = re.search(r'(\d+\.?\d*\s*кг)', dumbbell_name)
    weight_text = weight_match.group(1) if weight_match else dumbbell_name
    
    message_parts = [
        f"💪 Вы {equipment_type['action']} {weight_text}!",
        f"💰 Получено монет: {income_calculation['player_income']}",
        f"🦾 Получено силы: {income_calculation['power_gained']}",
        f"💲 Баланс: {format_number(player['balance'] + income_calculation['player_income'])}",
    ]

    if clan:
        message_parts.append(
            f"🏦 В казну клана: +{income_calculation['clan_income']} монет"
        )
        message_parts.append(
            f"⭐ Бонус клана: +{income_calculation.get('clan_bonus_coins', 0)} монет"
        )

    return "\n".join(message_parts)


@dumbbell_labeler.message(text=["прокачаться", "/прокачаться"])
async def upgrade_dumbbell_handler(message: Message):
    """Прокачать снаряд"""
    user_id = message.from_id
    player = await get_player(user_id)

    if not player:
        player = await create_player(user_id, str(message.from_id))

    current_level = player["dumbbell_level"]
    next_level = current_level + 1
    
    current_equipment = get_equipment_type(current_level)
    next_equipment = get_equipment_type(next_level) if next_level in settings.DUMBBELL_LEVELS else None

    if next_level not in settings.DUMBBELL_LEVELS:
        return "🏆 Вы уже достигли максимального уровня!"

    next_dumbbell = settings.DUMBBELL_LEVELS[next_level]

    if player["balance"] < next_dumbbell["price"]:
        return f"❌ Недостаточно монет. Нужно {format_number(next_dumbbell['price'])} 💰, у вас {format_number(player['balance'])} 💰"

    # Прокачиваем снаряд
    await update_player_balance(
        user_id,
        -next_dumbbell["price"],
        "dumbbell_upgrade",
        f"Прокачка до уровня {next_level}",
        None,
    )

    await update_dumbbell_level(user_id, next_level, next_dumbbell["name"])

    # Проверяем бонусы клана и рассчитываем общий доход
    clan = await get_player_clan(user_id)
    total_income = next_dumbbell['income_per_use']
    
    if clan:
        clan_bonuses = get_clan_bonuses(clan["level"])
        total_income += clan_bonuses['lift_bonus_coins']

    equipment_type = get_equipment_type(next_level)
    
    return (
        f"🎉 {equipment_type['name']} прокачана!\n"
        f"🤝 Новый уровень: {next_dumbbell['name']}\n"
        f"💰 Доход с учетом бонусов: {total_income} монет\n"
        f"🦾 Сила за подход: {next_dumbbell['power_per_use']}\n"
        f"💵 Потрачено: {format_number(next_dumbbell['price'])} монет"
    )
