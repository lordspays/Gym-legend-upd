import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from vkbottle.bot import BotLabeler, Message
from vkbottle import API

from bot.core.config import (
    settings, 
    INSPECTOR_LEVELS, 
    PROTECTION_LEVELS,
    INSPECTION_TIME_SETTINGS,
    NORMAL_SETTINGS
)
from bot.db import (
    get_player,
    update_player_balance,
    get_player_fitness_halls,
    update_fitness_halls,
    get_player_inspectors,
    buy_inspector_level,
    get_player_protections,
    buy_protection_level,
    get_active_protection,
    activate_protection,
    get_inspection_stats,
    update_inspection_stats,
    get_protection_stats,
    update_protection_stats,
    get_inspection_time_mode
)
from bot.utils import format_number, pointer_to_screen_name
from bot.services.clans import get_player_clan
from bot.services.users import is_admin

user_labeler = BotLabeler()
user_labeler.vbml_ignore_case = True

# ======================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================

def calculate_damage(inspector_level: int) -> int:
    """Рассчитать урон от инспектора"""
    level_info = INSPECTOR_LEVELS[inspector_level]
    if inspector_level == 1:
        # Для 1 уровня: 50% на 0, 50% на 1
        return 0 if random.random() < 0.5 else 1
    return random.randint(level_info["min_damage"], level_info["max_damage"])

def check_protection_success(protection_level: int, inspector_level: int, inspection_mode_active: bool) -> bool:
    """Проверить успешность защиты"""
    if inspection_mode_active:
        return False  # В режиме "Время проверок" защиты не работают
    
    protection_info = PROTECTION_LEVELS[protection_level]
    
    # Проверяем, защищает ли этот уровень от данного инспектора
    if inspector_level > protection_info["max_inspector_level"]:
        return False
    
    # Проверяем шанс защиты
    chance = random.randint(1, 100)
    return chance <= protection_info["chance"]

def get_current_settings():
    """Получить текущие настройки в зависимости от режима"""
    inspection_mode = get_inspection_time_mode()
    if inspection_mode["is_active"]:
        return INSPECTION_TIME_SETTINGS
    return NORMAL_SETTINGS

# ======================
# КОМАНДЫ ИГРОКОВ
# ======================

@user_labeler.message(text=["магазин инспекторов", "/магазин инспекторов"])
async def inspector_shop_handler(message: Message):
    """Показать магазин инспекторов"""
    shop_text = "🛒 МАГАЗИН ИНСПЕКТОРОВ\n\n"
    shop_text += "Доступные уровни инспекторов для подкупа:\n\n"
    
    for level in range(1, 6):
        inspector = INSPECTOR_LEVELS[level]
        shop_text += f"🎯 Уровень {level} - Цена: {inspector['price']} монет\n"
        shop_text += f"   ▫️ Урон: {inspector['min_damage']}-{inspector['max_damage']} фитнесс-зал"
        if inspector['min_damage'] == 0:
            shop_text += " (50% на 0, 50% на 1)"
        shop_text += "\n\n"
    
    shop_text += "💡 Пример: Подкупить проверку 3"
    
    await message.answer(shop_text)

@user_labeler.message(text=["подкупить проверку <level>", "/подкупить проверку <level>"])
async def buy_inspector_handler(message: Message, level: str):
    """Купить инспектора определенного уровня"""
    user_id = message.from_id
    
    try:
        inspector_level = int(level)
        if inspector_level not in INSPECTOR_LEVELS:
            return "❌ Неверный уровень инспектора! Доступные уровни: 1-5"
    except ValueError:
        return "❌ Уровень должен быть числом!"
    
    player = await get_player(user_id)
    if not player:
        return "❌ Игрок не найден"
    
    inspector_info = INSPECTOR_LEVELS[inspector_level]
    price = inspector_info["price"]
    
    # Проверяем баланс
    if player["balance"] < price:
        return f"❌ НЕДОСТАТОЧНО СРЕДСТВ\n\nНе хватает монет для подкупа инспектора!\n\n💰 Нужно: {price} монет\n💳 У вас: {player['balance']} монет"
    
    # Проверяем, не куплен ли уже этот уровень
    bought_inspectors = await get_player_inspectors(user_id)
    if inspector_level in bought_inspectors:
        return f"❌ У вас уже есть инспектор уровня {inspector_level}!"
    
    try:
        # Списываем деньги
        await update_player_balance(
            user_id,
            -price,
            "inspector_purchase",
            f"Покупка инспектора уровня {inspector_level}",
            None,
            None,
        )
        
        # Добавляем уровень инспектора
        success = await buy_inspector_level(user_id, inspector_level)
        if not success:
            return "❌ Ошибка при покупке инспектора"
        
        success_text = (
            f"💰 ПОДКУП ИНСПЕКТОРА\n\n"
            f"Инспектор уровня {inspector_level} успешно подкуплен!\n\n"
            f"🎯 Новый уровень инспектора: {inspector_level}\n"
            f"💰 Стоимость: {price} монет\n\n"
            f"✅ Теперь вы можете использовать инспекторов уровня {inspector_level}\n"
            f"💡 Используйте: Проверить [айди] [уровень]"
        )
        
        await message.answer(success_text)
        
    except Exception as e:
        return f"❌ Ошибка при покупке инспектора: {str(e)}"

@user_labeler.message(text=["проверить <cmd_args>", "/проверить <cmd_args>"])
async def inspect_handler(message: Message, cmd_args: str):
    """Проверить игрока"""
    user_id = message.from_id
    
    parts = cmd_args.strip().split()
    if len(parts) < 2:
        return "❌ Укажите айди игрока и уровень инспектора!\n📝 Использование: /проверить [айди] [уровень]"
    
    try:
        target_id = int(pointer_to_screen_name(parts[0]))
        inspector_level = int(parts[1])
    except ValueError:
        return "❌ Айди игрока и уровень инспектора должны быть числами!"
    
    # Проверяем себя
    if target_id == user_id:
        return "❌ Нельзя проверять самого себя!"
    
    # Проверяем уровень инспектора
    if inspector_level not in INSPECTOR_LEVELS:
        return "❌ Неверный уровень инспектора! Доступные уровни: 1-5"
    
    # Проверяем, есть ли у игрока этот уровень инспектора
    bought_inspectors = await get_player_inspectors(user_id)
    if inspector_level not in bought_inspectors:
        return f"❌ У вас нет инспектора уровня {inspector_level}!\n💡 Купите его в магазине инспекторов"
    
    # Получаем информацию об игроках
    player = await get_player(user_id)
    target_player = await get_player(target_id)
    
    if not player or not target_player:
        return "❌ Игрок не найден"
    
    # Проверяем, не в одном ли клане
    player_clan = await get_player_clan(user_id)
    target_clan = await get_player_clan(target_id)
    
    if player_clan and target_clan and player_clan["id"] == target_clan["id"]:
        return "❌ Нельзя проверять игроков своего клана!"
    
    # Получаем настройки в зависимости от режима
    inspection_mode = await get_inspection_time_mode()
    current_settings = INSPECTION_TIME_SETTINGS if inspection_mode["is_active"] else NORMAL_SETTINGS
    
    # Проверяем дневной лимит
    stats = await get_inspection_stats(user_id)
    
    if stats["inspections_today"] >= current_settings["daily_limit"]:
        return f"❌ Достигнут дневной лимит проверок!\n📊 Максимально в день: {current_settings['daily_limit']} проверок"
    
    # Проверяем кулдаун
    if stats.get("last_inspection"):
        last_time = datetime.fromisoformat(stats["last_inspection"])
        next_inspection = last_time + timedelta(minutes=current_settings["cooldown"])
        
        if datetime.now() < next_inspection:
            time_left = next_inspection - datetime.now()
            minutes_left = time_left.seconds // 60
            
            return (
                f"⏰ ПРОВЕРКА НЕДОСТУПНА\n\n"
                f"Вы недавно проводили проверку!\n\n"
                f"🕐 Время до следующей проверки: {minutes_left} минут\n"
                f"📊 Проведено проверок сегодня: {stats['inspections_today']}/{current_settings['daily_limit']}"
            )
    
    # Запускаем проверку
    await message.answer(
        f"🔍 ЗАПУСК ПРОВЕРКИ\n\n"
        f"Проверка игрока [id{target_id}|{target_player['username']}]\n"
        f"с инспектором уровня {inspector_level} начата!\n\n"
        f"🎯 Выбранный инспектор: Уровень {inspector_level}\n"
        f"⏱️ Проверка займет: 1 минута\n"
        f"💪 Максимальный урон: {INSPECTOR_LEVELS[inspector_level]['max_damage']} фитнесс-залов\n\n"
        f"Ожидайте результат в личных сообщениях"
    )
    
    # Имитируем задержку проверки
    await asyncio.sleep(1)
    
    # Проверяем защиту цели
    target_protection = await get_active_protection(target_id)
    protection_success = False
    
    if target_protection and target_protection["expires_at"]:
        protection_end = datetime.fromisoformat(target_protection["expires_at"])
        if datetime.now() < protection_end:
            protection_success = check_protection_success(
                target_protection["protection_level"], 
                inspector_level,
                inspection_mode["is_active"]
            )
    
    # Если защита сработала
    if protection_success:
        # Обновляем статистику для атакующего
        await update_inspection_stats(user_id, successful=False)
        
        # Обновляем статистику для защищающегося
        await update_protection_stats(target_id, blocked=True)
        
        # Сообщение атакующему
        await message.answer(
            f"🛡️ ПРОВЕРКА НЕ УДАЛАСЬ\n\n"
            f"Проверка игрока [id{target_id}|{target_player['username']}] провалена!\n\n"
            f"🎯 Ваш инспектор: Уровень {inspector_level}\n"
            f"🛡️ У игрока активна защита\n"
            f"💪 Все фитнесс-залы в безопасности\n\n"
            f"📊 Потери противника: 0 фитнесс-залов\n"
            f"💰 Компенсация игроку: 0 монет\n\n"
            f"⏱️ Следующая проверка через: {current_settings['cooldown']} минут"
        )
        
        # Уведомление защищающемуся в ЛС
        try:
            api = API(token=settings.VK_TOKEN)
            protection_name = PROTECTION_LEVELS[target_protection["protection_level"]]["name"]
            protection_end = datetime.fromisoformat(target_protection["expires_at"])
            time_left = protection_end - datetime.now()
            minutes_left = time_left.seconds // 60
            
            await api.messages.send(
                peer_id=target_id,
                message=(
                    f"🛡️ ПРОВЕРКА ОТБИТА\n\n"
                    f"Игрок [id{user_id}|{player['username']}] пытался проверить ваши залы!\n\n"
                    f"🎯 Уровень инспектора: {inspector_level}\n"
                    f"🛡️ Активная защита: {protection_name}\n"
                    f"✅ Проверка провалена благодаря защите\n"
                    f"💪 Все фитнесс-залы в безопасности\n\n"
                    f"📊 Ваши потери: 0 фитнесс-залов\n"
                    f"⏱️ Защита действует еще: {minutes_left} минут"
                ),
                random_id=0
            )
        except:
            pass
            
    else:
        # Защита не сработала - наносим урон
        damage = calculate_damage(inspector_level)
        current_halls = await get_player_fitness_halls(target_id)
        
        # Нельзя закрыть больше залов, чем есть у игрока
        damage = min(damage, current_halls)
        
        # Определяем компенсацию
        compensation_per_hall = current_settings["compensation_per_hall"]
        total_compensation = damage * compensation_per_hall
        
        if damage > 0:
            # Закрываем залы у цели
            await update_fitness_halls(target_id, -damage, 0)
            
            # Выплачиваем компенсацию цели
            await update_player_balance(
                target_id,
                total_compensation,
                "inspection_compensation",
                f"Компенсация за закрытые залы от проверки",
                None,
                user_id,
            )
        
        # Обновляем статистику для атакующего
        await update_inspection_stats(user_id, successful=True, halls_closed=damage)
        
        # Сообщение атакующему
        mode_note = " (в режиме)" if inspection_mode["is_active"] else ""
        response_text = (
            f"✅ РЕЗУЛЬТАТ ПРОВЕРКИ{mode_note}\n\n"
            f"Проверка игрока [id{target_id}|{target_player['username']}] завершена!\n\n"
            f"🎯 Уровень инспектора: {inspector_level}\n"
            f"💥 Закрыто фитнесс-залов: {damage}\n"
            f"💰 Компенсация игроку: {total_compensation} монет ({compensation_per_hall} × {damage})\n\n"
            f"⏱️ Следующая проверка через: {current_settings['cooldown']} минут\n"
            f"📈 Ваша статистика обновлена"
        )
        
        # Добавляем информацию о залах если они есть
        if damage > 0:
            new_halls_count = current_halls - damage
            response_text += f"\n📊 У игрока осталось: {new_halls_count} фитнесс-залов"
        
        await message.answer(response_text)
        
        # Уведомление цели в ЛС
        try:
            api = API(token=settings.VK_TOKEN)
            
            if damage > 0:
                message_text = (
                    f"⚠️ ПОСТУПИЛА ПРОВЕРКА\n\n"
                    f"Игрок [id{user_id}|{player['username']}] проверил ваши фитнесс-залы!\n\n"
                    f"🎯 Уровень инспектора: {inspector_level}\n"
                    f"💥 Закрыто фитнесс-залов: {damage}\n"
                    f"💰 Ваша компенсация: {total_compensation} монет ({compensation_per_hall} × {damage})\n\n"
                    f"📊 Теперь у вас: {current_halls - damage} фитнесс-залов\n"
                    f"🛡️ Рекомендуем приобрести защиту"
                )
            else:
                message_text = (
                    f"⚠️ ПОСТУПИЛА ПРОВЕРКА\n\n"
                    f"Игрок [id{user_id}|{player['username']}] проверил ваши фитнесс-залы!\n\n"
                    f"🎯 Уровень инспектора: {inspector_level}\n"
                    f"✅ Урон: 0 фитнесс-залов (повезло!)\n"
                    f"💰 Ваша компенсация: 0 монет\n\n"
                    f"📊 У вас осталось: {current_halls} фитнесс-залов"
                )
            
            await api.messages.send(
                peer_id=target_id,
                message=message_text,
                random_id=0
            )
        except:
            pass

@user_labeler.message(text=["инспекторы", "/инспекторы"])
async def inspectors_handler(message: Message):
    """Показать информацию об инспекторах игрока"""
    user_id = message.from_id
    
    bought_inspectors = await get_player_inspectors(user_id)
    stats = await get_inspection_stats(user_id)
    
    # Формируем список купленных уровней
    bought_text = "🎯 Арсенал подкупленных инспекторов:\n"
    for level in range(1, 6):
        if level in bought_inspectors:
            bought_text += f"   ▫️ Уровень {level} ✅ (куплен)\n"
        else:
            bought_text += f"   ▫️ Уровень {level} 🔒 (не куплен)\n"
    
    # Рассчитываем эффективность
    total_spent = sum(INSPECTOR_LEVELS[lvl]["price"] for lvl in bought_inspectors)
    efficiency = (stats["successful_inspections"] / stats["total_inspections"] * 100) if stats["total_inspections"] > 0 else 0
    
    inspectors_text = (
        f"📊 ВАШИ ИНСПЕКТОРЫ\n\n"
        f"{bought_text}\n"
        f"📈 Статистика проверок:\n"
        f"   ▫️ Всего проверок: {stats['total_inspections']}\n"
        f"   ▫️ Успешных проверок: {stats['successful_inspections']}\n"
        f"   ▫️ Неудачных проверок: {stats['failed_inspections']}\n\n"
        f"💥 Боевая эффективность:\n"
        f"   ▫️ Всего закрыто залов: {stats['halls_closed']}\n"
    )
    
    if stats['total_inspections'] > 0:
        inspectors_text += f"   ▫️ Средний урон за проверку: {stats['halls_closed']/stats['total_inspections']:.1f} зала\n"
    
    inspectors_text += f"   ▫️ Эффективность: {efficiency:.0f}%\n\n"
    inspectors_text += f"💰 Потрачено на подкуп: {total_spent} монет"
    
    await message.answer(inspectors_text)

@user_labeler.message(text=["магазин защиты", "/магазин защиты"])
async def protection_shop_handler(message: Message):
    """Показать магазин защиты"""
    
    shop_text = "🛒 МАГАЗИН ЗАЩИТЫ ОТ ПРОВЕРОК\n\n"
    shop_text += "Выберите уровень защиты для покупки:\n\n"
    
    for level in range(1, 6):
        protection = PROTECTION_LEVELS[level]
        shop_text += f"🛡️ Уровень {level} - {protection['name']}\n"
        shop_text += f"   ▫️ Цена: {protection['price']} монет\n"
        shop_text += f"   ▫️ Длительность: {protection['duration']} минут\n"
        shop_text += f"   ▫️ Защита от: Инспекторы 1-{protection['max_inspector_level']} уровня\n\n"
    
    shop_text += "💡 Пример: Защита зала 3"
    
    await message.answer(shop_text)

@user_labeler.message(text=["защита зала <level>", "/защита зала <level>"])
async def activate_protection_handler(message: Message, level: str):
    """Активировать защиту залов"""
    user_id = message.from_id
    
    try:
        protection_level = int(level)
        if protection_level not in PROTECTION_LEVELS:
            return "❌ Неверный уровень защиты! Доступные уровни: 1-5"
    except ValueError:
        return "❌ Уровень должен быть числом!"
    
    player = await get_player(user_id)
    if not player:
        return "❌ Игрок не найден"
    
    # Проверяем, куплена ли эта защита
    bought_protections = await get_player_protections(user_id)
    if protection_level not in bought_protections:
        return f"❌ У вас не куплена защита уровня {protection_level}!\n💡 Купите ее в магазине защиты"
    
    protection_info = PROTECTION_LEVELS[protection_level]
    price = protection_info["price"]
    
    # Проверяем баланс
    if player["balance"] < price:
        return f"❌ НЕДОСТАТОЧНО СРЕДСТВ\n\nНе хватает монет для активации защиты!\n\n💰 Нужно: {price} монет\n💳 У вас: {player['balance']} монет"
    
    # Проверяем, не активна ли уже защита
    active_protection = await get_active_protection(user_id)
    if active_protection and active_protection["expires_at"]:
        end_time = datetime.fromisoformat(active_protection["expires_at"])
        if datetime.now() < end_time:
            time_left = end_time - datetime.now()
            minutes_left = time_left.seconds // 60
            current_protection_name = PROTECTION_LEVELS[active_protection["protection_level"]]["name"]
            
            return f"❌ У вас уже активна защита!\n\n🛡️ Активная защита: {current_protection_name}\n⏱️ Осталось времени: {minutes_left} минут"
    
    try:
        # Списываем деньги
        await update_player_balance(
            user_id,
            -price,
            "protection_activation",
            f"Активация защиты уровня {protection_level}",
            None,
            None,
        )
        
        # Активируем защиту
        success = await activate_protection(user_id, protection_level, protection_info["duration"])
        if not success:
            return "❌ Ошибка при активации защиты"
        
        # Обновляем статистику расходов
        await update_protection_stats(user_id, spent=price)
        
        # Получаем обновленную защиту для времени
        active_protection = await get_active_protection(user_id)
        end_time = datetime.fromisoformat(active_protection["expires_at"])
        formatted_time = end_time.strftime("%H:%M")
        
        success_text = (
            f"⚡ АКТИВАЦИЯ ЗАЩИТЫ\n\n"
            f"Защита активирована успешно!\n\n"
            f"🛡️ Тип защиты: {protection_info['name']}\n"
            f"⏱️ Длительность: {protection_info['duration']} минут\n"
            f"🎯 Защита от: Инспекторы 1-{protection_info['max_inspector_level']} уровня\n\n"
            f"💰 Стоимость: {price} монет\n"
            f"✅ Защита активна до: {formatted_time}\n\n"
            f"🛡️ Защита работает до истечения времени\n"
            f"💪 Не снимается после атак"
        )
        
        await message.answer(success_text)
        
    except Exception as e:
        return f"❌ Ошибка при активации защиты: {str(e)}"

@user_labeler.message(text=["защитники", "/защитники"])
async def protectors_handler(message: Message):
    """Показать арсенал защиты"""
    user_id = message.from_id
    
    active_protection = await get_active_protection(user_id)
    bought_protections = await get_player_protections(user_id)
    protection_stats = await get_protection_stats(user_id)
    
    # Информация об активной защите
    active_text = ""
    if active_protection and active_protection["expires_at"]:
        end_time = datetime.fromisoformat(active_protection["expires_at"])
        if datetime.now() < end_time:
            protection_info = PROTECTION_LEVELS[active_protection["protection_level"]]
            time_left = end_time - datetime.now()
            minutes_left = time_left.seconds // 60
            
            active_text = (
                f"📊 Активная защита: {protection_info['name']}\n"
                f"⏱️ Осталось времени: {minutes_left} минут\n"
                f"🎯 Уровень защиты: {active_protection['protection_level']}\n\n"
            )
    
    # Список купленных защит
    bought_text = "📈 Купленные защиты:\n"
    if bought_protections:
        for level in sorted(bought_protections):
            protection_info = PROTECTION_LEVELS[level]
            bought_text += f"   ▫️ Уровень {level} ✅ ({protection_info['name']})\n"
    else:
        bought_text += "   ▫️ Нет купленных защит\n"
    
    protectors_text = (
        f"🛡️ ВАШ АРСЕНАЛ ЗАЩИТЫ\n\n"
        f"{active_text}"
        f"{bought_text}\n"
        f"💰 Всего потрачено на защиту: {protection_stats['total_spent_on_protection']} монет\n"
        f"📊 Всего отбито проверок: {protection_stats['total_blocked']}\n\n"
        f"💡 Используйте: Защита зала [уровень]"
    )
    
    await message.answer(protectors_text)

@user_labeler.message(text=["время проверки", "/время проверки"])
async def inspection_time_info_handler(message: Message):
    """Показать информацию о текущем режиме проверок"""
    inspection_mode = await get_inspection_time_mode()
    
    if inspection_mode["is_active"]:
        ends_at = datetime.fromisoformat(inspection_mode["ends_at"])
        time_left = ends_at - datetime.now()
        hours_left = time_left.seconds // 3600
        minutes_left = (time_left.seconds % 3600) // 60
        ends_at_formatted = ends_at.strftime("%H:%M")
        
        info_text = (
            f"⚡ РЕЖИМ 'ВРЕМЯ ПРОВЕРОК' АКТИВЕН\n\n"
            f"🎯 Активные настройки:\n"
            f"⏱️ КД проверок: 30 минут\n"
            f"📊 Лимит проверок: 24/сутки\n"
            f"💰 Компенсация: 6 монет/зал\n"
            f"🛡️ Защиты: Отключены\n\n"
            f"⏳ Осталось времени: {hours_left} часов {minutes_left} минут\n"
            f"🕐 Режим завершится в: {ends_at_formatted}"
        )
    else:
        info_text = (
            f"📊 РЕЖИМ ПРОВЕРОК\n\n"
            f"🎯 Обычные настройки:\n"
            f"⏱️ КД на проверки: 1 час\n"
            f"📊 Лимит проверок: 10/сутки\n"
            f"💰 Компенсация: 3 монеты/зал\n"
            f"🛡️ Защиты: Активны"
        )
    
    await message.answer(info_text)

# ======================
# ПЕРИОДИЧЕСКИЕ ЗАДАЧИ
# ======================

async def check_expired_protections():
    """Периодически проверять истекшие защиты"""
    while True:
        await asyncio.sleep(300)  # Проверять каждые 5 минут
        
        # В реальной реализации здесь был бы вызов функции очистки БД
        # await cleanup_expired_protections()
        pass

async def reset_daily_inspections_task():
    """Сбрасывать дневные счетчики проверок"""
    while True:
        now = datetime.now()
        # Ждем до следующего дня
        next_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (next_day - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        
        # В реальной реализации здесь был бы вызов функции сброса
        # await reset_all_daily_inspections()
        pass

# ======================
# ИНИЦИАЛИЗАЦИЯ
# ======================

async def init_inspection_system():
    """Инициализировать систему проверок"""
    # Запускаем фоновые задачи
    asyncio.create_task(check_expired_protections())
    asyncio.create_task(reset_daily_inspections_task())
    print("✅ Система проверок и защиты инициализирована")

# Экспортируем лейблер
__all__ = ["user_labeler", "init_inspection_system"]
