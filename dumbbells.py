from datetime import datetime

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


@dumbbell_labeler.message(text=["гантеля", "/гантеля"])
async def get_dumbbell_info_handler(message: Message):
    """Информация о гантели"""
    user_id = message.from_id
    player = await get_player(user_id)

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
        upgrade_info = f"🔜 Следующий уровень: {next_dumbbell['name']}\n💵 Цена: {format_number(next_dumbbell['price'])} монет\n💰 Доход за подход: {next_dumbbell['income_per_use']} монет"
    else:
        upgrade_info = "🏆 Вы достигли максимального уровня гантели!"

    # Проверяем бонусы клана
    clan = await get_player_clan(user_id)
    clan_bonus_text = ""
    if clan:
        clan_bonuses = get_clan_bonuses(clan["level"])
        clan_bonus_text = f"\n🏰 Бонус клана: +{clan_bonuses['lift_bonus_coins']} монет за поднятие"

    info_text = (
        f"🤝 Ваша гантеля:\n\n"
        f"{custom_note}"
        f"⚖️ Вес: {player['dumbbell_name']}\n"
        f"⭐ Уровень: {player['dumbbell_level']}\n"
        f"💰 Доход за подход: {income_per_use} монет{clan_bonus_text}\n"
        f"💪 Сила за подход: {dumbbell_info['power_per_use']}\n\n"
        f"{upgrade_info}"
    )

    return info_text


@dumbbell_labeler.message(text=["поднять", "/поднять"])
async def use_dumbbell_handler(message: Message):
    """Поднять гантелю"""
    user_id = message.from_id
    player = await get_player(user_id)

    # Проверка кулдауна
    last_use_str = player['last_dumbbell_use']
    if last_use_str:
        last_use = datetime.fromisoformat(last_use_str)
        seconds_passed = (datetime.now() - last_use).total_seconds()

        if seconds_passed < settings.DUMBBELL_COOLDOWN:
            seconds_left = int(settings.DUMBBELL_COOLDOWN - seconds_passed)
            return f'⏳ Время отдыха! Подождите {seconds_left} секунд'

    # Обрабатываем поднятие с новой системой кланов
    income_calculation = await process_dumbbell_lift_with_clan(user_id)

    # Формируем сообщение
    clan = await get_player_clan(user_id)
    message_parts = [
        f"💪 Вы подняли гантелю {player['dumbbell_name']}!",
        f"💰 Получено: {income_calculation['player_income']} монет",
        f"💪 Получено силы: {income_calculation['power_gained']}",
        f"📈 Баланс: {format_number(player['balance'] + income_calculation['player_income'])} монет",
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
    """Прокачать гантелю"""
    user_id = message.from_id
    player = await get_player(user_id)

    if not player:
        player = await create_player(user_id, str(message.from_id))

    current_level = player["dumbbell_level"]
    next_level = current_level + 1

    if next_level not in settings.DUMBBELL_LEVELS:
        return "🏆 Вы уже достигли максимального уровня гантели!"

    next_dumbbell = settings.DUMBBELL_LEVELS[next_level]

    if player["balance"] < next_dumbbell["price"]:
        return f"❌ Недостаточно монет. Нужно {format_number(next_dumbbell['price'])} 💰, у вас {format_number(player['balance'])} 💰"

    # Прокачиваем гантелю
    await update_player_balance(
        user_id,
        -next_dumbbell["price"],
        "dumbbell_upgrade",
        f"Прокачка гантели до уровня {next_level}",
        None,
    )

    await update_dumbbell_level(user_id, next_level, next_dumbbell["name"])

    # Проверяем бонусы клана
    clan = await get_player_clan(user_id)
    clan_bonus_text = ""
    if clan:
        clan_bonuses = get_clan_bonuses(clan["level"])
        clan_bonus_text = f"\n🏰 С бонусом клана: {next_dumbbell['income_per_use'] + clan_bonuses['lift_bonus_coins']} монет за подход"

    return (
        f"🎉 Гантеля прокачана!\n"
        f"🤝 Новый уровень: {next_dumbbell['name']}\n"
        f"💰 Доход за подход: {next_dumbbell['income_per_use']} монет{clan_bonus_text}\n"
        f"💪 Сила за подход: {next_dumbbell['power_per_use']}\n"
        f"💵 Потрачено: {format_number(next_dumbbell['price'])} монет"
  )
