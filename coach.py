import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from vkbottle.bot import BotLabeler, Message

from bot.db import (
    get_player,
    update_player_balance,
    get_player_fitness_halls,
    update_fitness_halls,
    get_coach_level,
    update_coach_level,
    get_last_training_time,
    set_last_training_time,
    get_coach_stats,
)
from bot.utils import format_number

coach_labeler = BotLabeler()
coach_labeler.vbml_ignore_case = True


# ======================
# КОНСТАНТЫ ТРЕНЕРСКОЙ ДЕЯТЕЛЬНОСТИ
# ======================

COACH_LEVELS = {
    1: {"name": "Посетитель", "price": 25, "min_income": 2, "max_income": 5, "bonus_chance": 0, "bonus_halls": 0},
    2: {"name": "Ученик", "price": 50, "min_income": 5, "max_income": 8, "bonus_chance": 0, "bonus_halls": 0},
    3: {"name": "Помощник тренера", "price": 75, "min_income": 7, "max_income": 13, "bonus_chance": 0, "bonus_halls": 0},
    4: {"name": "Начинающий групповой тренер", "price": 85, "min_income": 11, "max_income": 15, "bonus_chance": 0, "bonus_halls": 0},
    5: {"name": "Групповой тренер", "price": 100, "min_income": 14, "max_income": 18, "bonus_chance": 0, "bonus_halls": 0},
    6: {"name": "Персональный тренер", "price": 125, "min_income": 16, "max_income": 20, "bonus_chance": 10, "bonus_halls": 3},
    7: {"name": "Старший тренер", "price": 175, "min_income": 18, "max_income": 25, "bonus_chance": 15, "bonus_halls": 3},
    8: {"name": "Частный тренер", "price": 250, "min_income": 25, "max_income": 30, "bonus_chance": 15, "bonus_halls": 5},
    9: {"name": "Подготовка к всероссийским соревнованиям", "price": 300, "min_income": 30, "max_income": 40, "bonus_chance": 13, "bonus_halls": 10},
    10: {"name": "Обучение олимпийских призёров", "price": 500, "min_income": 50, "max_income": 75, "bonus_chance": 25, "bonus_halls": 10},
}

# ИЗМЕНЕНО: КД тренировки теперь 1 час вместо 3 часов
TRAINING_COOLDOWN = timedelta(hours=1)


# ======================
# КОМАНДЫ ТРЕНЕРСКОЙ ДЕЯТЕЛЬНОСТИ
# ======================

@coach_labeler.message(text=["персональный магазин", "/персональный магазин"])
async def personal_shop_handler(message: Message):
    """Показать доступные уровни тренерской деятельности"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    if not player:
        return "❌ Игрок не найден"
    
    current_level = await get_coach_level(user_id)
    
    shop_text = "🎓 ПЕРСОНАЛЬНЫЙ МАГАЗИН\n\nДоступные уровни тренерской деятельности:\n\n"
    
    for level in range(1, 11):
        coach_data = COACH_LEVELS[level]
        
        if level == current_level:
            prefix = "✅ "
        elif level < current_level:
            prefix = "✔️ "
        else:
            prefix = "🔘 "
        
        shop_text += f"{prefix}{level}. {coach_data['name']}\n"
        shop_text += f"💰 Цена: {coach_data['price']} монет\n"
        
        if coach_data['bonus_chance'] > 0:
            shop_text += f"🎁 Бонус: {coach_data['bonus_chance']}% шанс на {coach_data['bonus_halls']} фитнес-зала\n"
        
        shop_text += "\n"
    
    shop_text += f"💡 Используйте: Стаж - купить следующий уровень\n"
    shop_text += f"📊 Текущий уровень: {current_level if current_level > 0 else 'Нет'}"
    
    await message.answer(shop_text)


@coach_labeler.message(text=["стаж", "/стаж"])
async def upgrade_coach_handler(message: Message):
    """Повысить уровень тренерской деятельности"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    if not player:
        return "❌ Игрок не найден"
    
    current_level = await get_coach_level(user_id)
    
    # Если у игрока нет тренерской деятельности
    if current_level == 0:
        next_level = 1
    else:
        next_level = current_level + 1
    
    # Проверяем максимальный уровень
    if next_level > 10:
        return "🎓 ТРЕНЕРСКАЯ ДЕЯТЕЛЬНОСТЬ\n\nВы достигли максимального уровня тренера!"
    
    coach_data = COACH_LEVELS[next_level]
    price = coach_data["price"]
    
    # Проверяем баланс
    if player["balance"] < price:
        return f"❌ НЕДОСТАТОЧНО СРЕДСТВ\n\nНе хватает монет для покупки уровня!\n\n💰 Нужно: {price} монет\n💳 У вас: {player['balance']} монет"
    
    try:
        # Списываем деньги
        await update_player_balance(
            user_id,
            -price,
            "coach_upgrade",
            f"Покупка уровня тренера: {coach_data['name']}",
            None,
            None,
        )
        
        # Обновляем уровень тренера
        await update_coach_level(user_id, next_level)
        
        success_text = (
            f"🎓 ТРЕНЕРСКАЯ ДЕЯТЕЛЬНОСТЬ\n\n"
            f"Поздравляю! Вы стали {coach_data['name']}!\n\n"
            f"💰 С баланса списано: {price} монет\n"
            f"🏆 Новый уровень: {next_level} ({coach_data['name']})\n"
            f"⏰ КД тренировок: 1 час"
        )
        
        await message.answer(success_text)
        
    except Exception as e:
        return f"❌ Ошибка при покупке уровня: {str(e)}"


@coach_labeler.message(text=["тренировка", "треня", "/тренировка", "/треня"])
async def training_handler(message: Message):
    """Провести тренировку"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    if not player:
        return "❌ Игрок не найден"
    
    # Проверяем наличие тренерской деятельности
    current_level = await get_coach_level(user_id)
    if current_level == 0:
        return "❌ ОШИБКА\n\nУ вас нет тренерской деятельности!\n\n💡 Используйте: Персональный магазин\n🔹 Просмотреть доступные уровни\n🔹 Купить уровень командой: Стаж"
    
    # Проверяем КД
    last_training = await get_last_training_time(user_id)
    if last_training:
        last_time = datetime.fromisoformat(last_training)
        next_training = last_time + TRAINING_COOLDOWN
        
        if datetime.now() < next_training:
            time_left = next_training - datetime.now()
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            next_time = next_training.strftime("%H:%M")
            
            cooldown_text = (
                f"⏰ КОМАНДА НЕДОСТУПНА\n\n"
                f"По расписанию нет тренировок.\n\n"
                f"🕐 Ближайшая тренировка через: {hours_left} ч {minutes_left} мин\n"
                f"📅 Можно провести в: {next_time}"
            )
            return cooldown_text
    
    coach_data = COACH_LEVELS[current_level]
    
    try:
        # Проверяем бонус
        got_bonus = False
        if coach_data["bonus_chance"] > 0:
            bonus_roll = random.randint(1, 100)
            if bonus_roll <= coach_data["bonus_chance"]:
                got_bonus = True
        
        if got_bonus:
            # Даем бонусные фитнес-залы
            bonus_halls = coach_data["bonus_halls"]
            current_halls = await get_player_fitness_halls(user_id)
            new_halls_count = await update_fitness_halls(user_id, bonus_halls, 0)  # Цена 0 для бонусных
            
            success_text = (
                f"🎮 ТРЕНИРОВКА\n\n"  # ЗАМЕНЕНО: 🏃‍♂️ на 🎮
                f"Тренировка завершена успешно!\n\n"
                f"🎁 Бонус: Получено {bonus_halls} фитнес-зала!\n"
                f"⏰ Следующая тренировка через: 1 час"
            )
        else:
            # Даем обычный доход
            income = random.randint(coach_data["min_income"], coach_data["max_income"])
            
            await update_player_balance(
                user_id,
                income,
                "training_income",
                f"Доход от тренировки (уровень {current_level})",
                None,
                None,
            )
            
            success_text = (
                f"🎮 ТРЕНИРОВКА\n\n"  # ЗАМЕНЕНО: 🏃‍♂️ на 🎮
                f"Тренировка завершена успешно!\n\n"
                f"💵 Получено: {income} монет\n"
                f"⏰ Следующая тренировка через: 1 час"
            )
        
        # Обновляем время последней тренировки
        await set_last_training_time(user_id, datetime.now().isoformat())
        
        await message.answer(success_text)
        
    except Exception as e:
        return f"❌ Ошибка при проведении тренировки: {str(e)}"


@coach_labeler.message(text=["портфолио", "/портфолио"])
async def portfolio_handler(message: Message):
    """Информация о тренерской деятельности"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    if not player:
        return "❌ Игрок не найден"
    
    current_level = await get_coach_level(user_id)
    if current_level == 0:
        return "❌ ОШИБКА\n\nУ вас нет тренерской деятельности!\n\n💡 Используйте: Персональный магазин\n🔹 Просмотреть доступные уровни\n🔹 Купить уровень командой: Стаж"
    
    coach_data = COACH_LEVELS[current_level]
    
    # Проверяем время до следующей тренировки
    last_training = await get_last_training_time(user_id)
    time_until_training = "Готова"
    
    if last_training:
        last_time = datetime.fromisoformat(last_training)
        next_training = last_time + TRAINING_COOLDOWN
        
        if datetime.now() < next_training:
            time_left = next_training - datetime.now()
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            time_until_training = f"{hours_left} ч {minutes_left} мин"
            next_time = next_training.strftime("%H:%M")
        else:
            next_time = "Сейчас"
    else:
        next_time = "Сейчас"
    
    # Следующий уровень
    next_level = current_level + 1 if current_level < 10 else None
    next_price = COACH_LEVELS[next_level]["price"] if next_level else "Макс."
    
    portfolio_text = (
        f"📋 ПОРТФОЛИО ТРЕНЕРА\n\n"
        f"🎓 Должность: {coach_data['name']}\n"
        f"⭐ Уровень: {current_level}\n"
        f"💰 Цена следующей прокачки: {next_price} монет\n"
        f"💵 Доход от тренировки: {coach_data['min_income']}-{coach_data['max_income']} монет\n"
    )
    
    if coach_data['bonus_chance'] > 0:
        portfolio_text += f"🎯 Шанс на бонус: {coach_data['bonus_chance']}%\n"
    else:
        portfolio_text += f"🎯 Шанс на бонус: Нет\n"
    
    portfolio_text += f"\n⏰ Время до тренировки: {time_until_training}\n"
    portfolio_text += f"🕐 Можно провести в: {next_time}"
    
    await message.answer(portfolio_text)
