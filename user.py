import re
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from vkbottle.bot import BotLabeler, Message

from bot.core.config import settings
from bot.db import (
    create_player,
    get_player,
    get_player_clan,
    update_player_balance,
    update_username,
    set_info_access,
    get_info_access_status,
    remove_info_access,
    update_fitness_halls,
    get_player_fitness_halls,
    get_daily_purchases,
)
from bot.services.clans import (
    get_clan_bonuses,
)
from bot.services.users import is_admin
from bot.utils import format_number, pointer_to_screen_name

user_labeler = BotLabeler()
user_labeler.vbml_ignore_case = True


# ======================
# КОМАНДА ИНФА
# ======================

@user_labeler.message(text=["инфа <cmd_args>", "/инфа <cmd_args>"])
async def player_info_handler(message: Message, cmd_args: str):
    """Полная информация об игроке"""
    user_id = message.from_id
    
    has_access = await get_info_access_status(user_id)
    
    if not has_access:
        return "❌ У вас нет доступа к этой команде!\n\n💡 Для получения доступа обратитесь к администратору:\n👮 Администратор может выдать доступ командой:\n/доступ_инфа [айди_игрока]"

    try:
        target_id = int(pointer_to_screen_name(cmd_args))
    except ValueError:
        return "❌ Айди игрока должно быть числом!"

    target_player = await get_player(target_id)

    if not target_player:
        return "❌ Игрок с таким айди не найден!"

    # Получаем количество фитнес-залов
    fitness_halls = await get_player_fitness_halls(target_id)
    daily_income_from_halls = fitness_halls * 10  # 10 монет за каждый зал в день
    
    clan = await get_player_clan(target_id)

    created_date = datetime.fromisoformat(target_player["created_at"]).strftime("%d.%m.%Y %H:%M")
    last_active = target_player.get("last_active")
    if last_active:
        last_active_date = datetime.fromisoformat(last_active).strftime("%d.%m.%Y %H:%M")
        days_inactive = (datetime.now() - datetime.fromisoformat(last_active)).days
        if days_inactive == 0:
            last_active_text = f"{last_active_date} (сегодня)"
        else:
            last_active_text = f"{last_active_date} ({days_inactive} дней назад)"
    else:
        last_active_text = "Никогда"

    admin_level = target_player.get("admin_level", 0)
    admin_status = "👑 Создатель🌟" if admin_level == 2 else "👮 Администратор" if admin_level == 1 else "❌ Нет"
    
    banned_status = "✅ Нет" if target_player.get("is_banned", 0) == 0 else "🚫 Да"

    if target_player.get("custom_income") is not None:
        income_per_use = f"{target_player['custom_income']} монет ⚡"
    else:
        income_per_use = f"{settings.DUMBBELL_LEVELS[target_player['dumbbell_level']]['income_per_use']} монет"

    info_text = (
        f"📊 ПОЛНАЯ ИНФОРМАЦИЯ ОБ ИГРОКЕ 📊\n"
        f"𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃\n\n"
        
        f"💻 Основная информация:\n"
        f"🔸 Никнейм: [id{target_player['user_id']}|{target_player['username']}]\n"
        f"🔸 Уровень админа: {admin_status}\n"
        f"🔸 Забанен: {banned_status}\n"
        f"🔸 Дата регистрации: {created_date}\n"
        f"🔸 Последняя активность: {last_active_text}\n\n"
        
        f"💰 Экономика:\n"
        f"🎗️ Баланс: {format_number(target_player['balance'])} монет\n"
        f"🎗️ Фитнес-залы: {format_number(fitness_halls)} шт.\n"
        f"🎗️ Ежедневный доход с залов: {format_number(daily_income_from_halls)} монет\n"
        f"🎗️ Всего заработано: {format_number(target_player.get('total_earned', 0))} монет\n"
        f"🎗️ Всего потрачено: {format_number(target_player.get('total_spent', 0))} монет\n\n"
        
        f"💪 Прогресс:\n"
        f"⚖️ Сила: {format_number(target_player['power'])}\n"
        f"⚖️ Гантеля: {target_player['dumbbell_name']} (Уровень: {target_player['dumbbell_level']})\n"
        f"⚖️ Поднятий: {format_number(target_player['total_lifts'])}\n"
        f"⚖️ Доход за подход: {income_per_use}\n"
    )

    if clan:
        info_text += (
            f"\n🏰 Клан:\n"
            f"🛡️ Название: [{clan['tag']}] {clan['name']}\n"
            f"🛡️ Уровень клана: {clan['level']}\n"
            f"🛡️ Вклад в казну: {format_number(target_player.get('clan_contributions', 0))} монет\n"
        )

    await message.answer(info_text, disable_mentions=True)


# ======================
# КОМАНДА ПОКУПКИ ФИТНЕС-ЗАЛОВ
# ======================

@user_labeler.message(text=["купить зал <amount>", "купить залы <amount>", "/купить зал <amount>"])
async def buy_fitness_halls_handler(message: Message, amount: str):
    """Покупка фитнес-залов"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    if not player:
        return "❌ Игрок не найден"
    
    try:
        halls_to_buy = int(amount)
        if halls_to_buy <= 0:
            return "❌ Количество должно быть положительным числом!"
    except ValueError:
        return "❌ Укажите число залов для покупки!"
    
    daily_purchases = await get_daily_purchases(user_id)
    if daily_purchases + halls_to_buy > 100:
        return f"❌ Достигнут дневной лимит покупок!\n\n📊 Максимально в день: 100 фитнес залов\n🎯 Вы уже купили: {daily_purchases} сегодня"
    
    current_halls = await get_player_fitness_halls(user_id)
    
    start_price = 35
    price_increment = 5
    total_price = halls_to_buy * (2 * start_price + (halls_to_buy - 1) * price_increment) // 2
    
    if player["balance"] < total_price:
        return f"❌ Недостаточно средств для покупки!\n\n💰 Нужно: {format_number(total_price)} монет\n💳 У вас: {format_number(player['balance'])} монет"
    
    try:
        new_halls_count = await update_fitness_halls(user_id, halls_to_buy, total_price)
        
        await update_player_balance(
            user_id,
            -total_price,
            "fitness_hall_purchase",
            f"Покупка {halls_to_buy} фитнес залов",
            None,
            None,
        )
        
        daily_income = new_halls_count * 10
        
        hall_word = "залов" if halls_to_buy > 1 else "зала"
        success_text = (
            f"⚖️ ФИТНЕС-ЗАЛЫ\n\n"
            f"Поздравляю, успешная покупка {halls_to_buy} фитнес {hall_word}!\n\n"
            f"💰 С баланса списано: {format_number(total_price)} монет\n"
            f"📈 Теперь у вас: {format_number(new_halls_count)} фитнес залов\n"
            f"💵 Ежедневный доход: {format_number(daily_income)} монет/день"
        )
        
        await message.answer(success_text, disable_mentions=True)
        
    except Exception as e:
        return f"❌ Ошибка при покупке: {str(e)}"


# ======================
# КОМАНДА ПЕРЕВОДА ДЕНЕГ
# ======================

@user_labeler.message(
    text=[
        "перевод <cmd_args>",
        "перевести <cmd_args>",
        "/перевод <cmd_args>",
        "/перевести <cmd_args>",
    ]
)
async def transfer_money_handler(message: Message, cmd_args: str):
    """Перевод денег другому игроку"""
    parts = cmd_args.strip().split()

    if len(parts) < 2:
        return "❌ Укажите айди игрока и сумму перевода!\n📝 Использование: /перевод [айди] [сумма]"

    try:
        target_id = int(pointer_to_screen_name(parts[0]))
    except ValueError:
        return "❌ Айди игрока должно быть числом!"

    amount_str = parts[1]
    user_id = message.from_id

    try:
        amount = int(amount_str)
        if amount <= 0:
            return "❌ Сумма перевода должна быть положительным числом!"
    except ValueError:
        return "❌ Сумма перевода должна быть числом!"

    player = await get_player(user_id)

    if player["balance"] < amount:
        return f"❌ Недостаточно средств для перевода!\n💰 Нужно: {format_number(amount)} монет\n💳 У вас: {format_number(player['balance'])} монет"

    if amount < 10:
        return "❌ Минимальная сумма перевода - 10 монет!"

    target_player = await get_player(target_id)

    if not target_player:
        return '❌ Игрок с таким айди не найден!'

    target_username = target_player["username"]

    if target_player.get("is_banned", 0) == 1:
        return "❌ Нельзя переводить деньги забаненному игроку!"

    commission = max(1, int(amount * 0.05))
    net_amount = amount - commission

    try:
        await update_player_balance(
            user_id,
            -amount,
            "money_transfer_sent",
            f"Перевод игроку {target_username}",
            None,
            target_id,
        )

        await update_player_balance(
            target_id,
            net_amount,
            "money_transfer_received",
            f"Перевод от игрока {player['username']}",
            None,
            user_id,
        )

        response_text = (
            f"💸 Перевод выполнен успешно!\n\n"
            f"👤 Отправитель: [id{player['user_id']}|{player['username']}]\n"
            f"👥 Получатель: [id{target_id}|{target_username}]\n"
            f"💰 Сумма: {format_number(amount)} монет\n"
            f"📊 Комиссия (5%): {format_number(commission)} монет\n"
            f"💳 Зачислено: {format_number(net_amount)} монет\n"
            f"🏦 Ваш баланс: {format_number(player['balance'] - amount)} монет\n\n"
            f"✅ Деньги успешно переведены!"
        )
        await message.answer(response_text, disable_mentions=True)
    except Exception as e:
        return f"❌ Ошибка при выполнении перевода: {str(e)}"


# ======================
# ОБЫЧНЫЕ КОМАНДЫ
# ======================

@user_labeler.message(text=["начать", "/начать"])
async def welcome_handler(message: Message):
    """Приветственное сообщение"""
    user_id = message.from_id

    player = await get_player(user_id)
    if not player:
        # При регистрации выдаем ник "Игрок"
        player = await create_player(user_id, "Игрок")

    welcome_text = (
        f"👋Привет! [id{user_id}|{player['username']}], ты попал в \n"
        f"𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃 💪\n\n"
        f"💪 Здесь ты можешь стать легендой фитнес-индустрии, Качком и Бизнесменом!\n\n"
        f"📒 Твой ник: [id{user_id}|{player['username']}]\n"
        f"💰 Стартовый баланс: {format_number(player['balance'])} монет\n"
        f"⚖️ Стартовая гантеля: {player['dumbbell_name']}\n\n"
        f"❓ Как играть:\n\n"
        f"🥇 Первым делом тебе нужно узнать основные команды бота (Помощь)\n"
        f"🥈 Начнем твои первые шаги к Королю мышц (Поднять)\n"
        f"🥉 Купи свой первый фитнес зал (Купить зал 1)\n"
        f"🏅 Создай или вступи в свой первый клан (К помощь)\n"
        f"🏅 Соревнуйся с другими (Топ)\n\n"
        f"👨‍💻 Напиши команду Помощь, чтобы узнать все команды подробнее. Удачи в развитии! 🫶"
    )

    await message.answer(welcome_text, disable_mentions=True)


@user_labeler.message(text=["профиль", "/профиль"])
async def get_profile_handler(message: Message):
    """Профиль игрока"""
    user_id = message.from_id
    player = await get_player(user_id)

    if not player:
        return "❌ Игрок не найден"

    fitness_halls = await get_player_fitness_halls(user_id)
    
    if player.get("custom_income") is not None:
        income_per_use = player["custom_income"]
        income_note = f"💰 Доход за подход: {income_per_use} монет ⚡\n"
    else:
        dumbbell_info = settings.DUMBBELL_LEVELS[player["dumbbell_level"]]
        income_per_use = dumbbell_info["income_per_use"]
        income_note = f"💰 Доход за подход: {income_per_use} монет\n"

    clan = await get_player_clan(user_id)
    clan_info = ""
    if clan:
        clan_info = f"🏰 Клан: [{clan['tag']}] {clan['name']}\n"

    created_date = datetime.fromisoformat(player["created_at"]).strftime("%d.%m.%Y")

    admin_level = player.get("admin_level", 0)
    if admin_level > 0:
        privileges = "👨‍💻 Администратор"
    else:
        privileges = "Игрок"

    profile_text = (
        f"📑 Профиль игрока\n\n"
        f"💻 Игровой никнейм: [id{player['user_id']}|{player['username']}]\n"
        f"💎 Привилегии: {privileges}\n"
        f"💰 Баланс: {format_number(player['balance'])} монет\n"
        f"💪 Сила: {format_number(player['power'])}\n"
        f"🏦 Фитнесс залы: {format_number(fitness_halls)}\n"
        f"⚖️ Гантеля: {player['dumbbell_name']} (Уровень: {player['dumbbell_level']})\n"
        f"{income_note}"
        f"👨‍💻 Поднятий гантели: {format_number(player['total_lifts'])}\n"
        f"📅 Дата регистрации: {created_date}"
    )

    await message.answer(profile_text, disable_mentions=True)


@user_labeler.message(text=["баланс", "/баланс"])
async def get_balance_handler(message: Message):
    """Баланс игрока"""
    user_id = message.from_id
    player = await get_player(user_id)

    return f"💰 Ваш баланс: {format_number(player['balance'])} монет"


@user_labeler.message(text=["помощь", "/помощь"])
async def get_help_handler(message: Message):
    """Справка по командам"""
    commands = [
        "𝐆𝐘𝐌 𝐋𝐄𝐆𝐄𝐍𝐃 - Доступные команды:\n",
        "📊 Профиль и информация:",
        "📒 Профиль - ваш профиль",
        "📒 Баланс - текущий баланс",
        "📒 Купить зал [кол-во] - купить фитнес-залы\n",
        "🎓 Тренерская деятельность:",
        "📒 Персональный магазин - доступные уровни",
        "📒 Стаж - повысить уровень тренера",
        "📒 Тренировка - провести тренировку",
        "📒 Портфолио - информация о тренерстве\n",
        "💪 Гантели:",
        "🔸 Гантеля - информация о гантеле",
        "🔸 Поднять - поднять гантелю",
        "🔸 Прокачаться - улучшить гантелю",
        "🔸 Магазин - магазин гантелей\n",
        "🏰 Кланы:",
        "🔹 К создать [ТЭГ] [название] - создать клан",
        "🔹 К улучшить - улучшить уровень клана",
        "🔹 К профиль - информация о клане",
        "🔹 К помощь - справка по кланам",
        "🔹 К топ - топ кланов",
        "🔹 К положить [сумма] - положить деньги в казну\n",
        "🔍 Проверки:",
        "🔸 Магазин инспекторов - доступные уровни инспекторов",
        "🔸 Подкупить проверку [уровень] - купить инспектора",
        "🔸 Проверить [айди] [уровень] - проверить игрока",
        "🔸 Инспекторы - информация о ваших инспекторах",
        "⏰ Время проверки - текущий режим проверок\n",
        "🛡️ Защита:",
        "🔹 Магазин защиты - доступные уровни защиты",
        "🔹 Защита зала [уровень] - активировать защиту",
        "🔹 Защитники - информация о вашей защите\n",
        "💰 Ежедневные выплаты:",
        "📒 Доход залы - статистика ежедневного дохода\n",
        "💸 Перевод денег:",
        "📗 Перевод [айди] [сумма] - перевести деньги",
        "📗 Перевести [айди] [сумма] - перевести деньги\n",
        "🎫 Промокоды:",
        "👑 Промо [код] - активировать промокод\n",
        "🏆 Рейтинги:",
        "🥇 Топ - общий список рейтингов",
        "🥇 Топ монет - топ по балансу",
        "🥇 Топ поднятий - топ по поднятиям",
        "🥇 Топ заработка - топ по заработку",
        "🥇 К топ - топ кланов",
    ]
    
    user_id = message.from_id
    has_access = await get_info_access_status(user_id)
    
    if has_access:
        commands.insert(6, "📒 Инфа [айди] - полная информация об игроке")

    return "\n".join(commands)


@user_labeler.message(text=["магазин", "/магазин"])
async def get_dumbbell_shop_handler(message: Message):
    """Магазин гантелей"""
    user_id = message.from_id
    player = await get_player(user_id)

    if not player:
        player = await create_player(user_id, "Игрок")

    current_level = player["dumbbell_level"]

    shop_items = []
    for level in range(1, 21):
        dumbbell = settings.DUMBBELL_LEVELS[level]

        if level == current_level:
            prefix = "✅ "
        elif level < current_level:
            prefix = "✔️ "
        else:
            prefix = "🔘 "

        if level == current_level:
            suffix = " (Ваш текущий)"
        elif player["balance"] >= dumbbell["price"]:
            suffix = " 🔥"
        else:
            suffix = " ⏳"

        shop_items.append(
            f"{prefix}Уровень {level}: {dumbbell['name']}\n"
            f"   ⚖️ Вес: {dumbbell['weight']} | "
            f"💰 Доход: {dumbbell['income_per_use']} монет | "
            f"💪 Сила: {dumbbell['power_per_use']} | "
            f"💵 Цена: {format_number(dumbbell['price'])} монет{suffix}"
        )

    shop_text = (
        "🛒 Магазин гантелей🛍️\n\n"
        "💪 Как прокачаться:\n"
        "1. Копи монеты (Поднять)\n"
        "2. Покупаешь улучшение (Прокачаться)\n"
        "3. Получаешь больше дохода!\n\n"
        "📖 Доступные гантели:\n"
        + "\n".join(shop_items)
        + f"\n\n💰 Ваш баланс: {format_number(player['balance'])} монет\n"
        f"Текущая гантеля: {player['dumbbell_name']}"
    )

    return shop_text


@user_labeler.message(text=["гник <cmd_args>", "/гник <cmd_args>"])
async def change_username_handler(message: Message, cmd_args: str):
    """Изменить ник"""
    user_id = message.from_id
    new_username = cmd_args.strip()

    if not new_username:
        return "❌ Укажите новый ник!\n📝 Использование: /гник [новый_ник]"

    if len(new_username) > 20:
        return "❌ Ник не может быть длиннее 20 символов!"

    if len(new_username) < 3:
        return "❌ Ник должен быть не короче 3 символов!"

    if re.search(r'[@#$%^&*()+=|\\<>{}[\]:;"\'?/~`]', new_username):
        return "❌ Ник не может содержать специальные символы!\n✅ Разрешены: буквы, цифры, пробелы, дефисы, подчеркивания"

    if new_username != new_username.strip():
        return "❌ Ник не может начинаться или заканчиваться пробелом!"

    if "  " in new_username:
        return "❌ Ник не может содержать несколько пробелов подряд!"

    if not re.match(r"^[a-zA-Zа-яА-ЯёЁ0-9 _-]+$", new_username):
        return "❌ Ник содержит недопустимые символы!\n✅ Разрешены: буквы, цифры, пробелы, дефисы, подчеркивания"

    await update_username(user_id, new_username)

    return f"✅ Ваш ник изменен на: {new_username}"
