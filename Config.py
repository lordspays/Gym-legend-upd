# ======================
# КОНСТАНТЫ СИСТЕМЫ ПРОВЕРОК И ЗАЩИТЫ
# ======================

INSPECTOR_LEVELS = {
    1: {"price": 3, "min_damage": 0, "max_damage": 1},
    2: {"price": 6, "min_damage": 1, "max_damage": 2},
    3: {"price": 15, "min_damage": 3, "max_damage": 5},
    4: {"price": 50, "min_damage": 5, "max_damage": 7},
    5: {"price": 100, "min_damage": 8, "max_damage": 10},
}

PROTECTION_LEVELS = {
    1: {"name": "Привести все залы в порядок", "price": 35, "duration": 15, "chance": 10, "max_inspector_level": 2},
    2: {"name": "Слухи о подкупе", "price": 75, "duration": 30, "chance": 15, "max_inspector_level": 3},
    3: {"name": "У нас все четко", "price": 100, "duration": 30, "chance": 20, "max_inspector_level": 4},
    4: {"name": "Заплатить больше другого", "price": 175, "duration": 60, "chance": 40, "max_inspector_level": 5},
    5: {"name": "Свои люди в прокуратуре", "price": 350, "duration": 60, "chance": 100, "max_inspector_level": 5},
}

# Настройки режимов
INSPECTION_TIME_SETTINGS = {
    "cooldown": 30,  # минут в режиме "Время проверок"
    "daily_limit": 24,
    "compensation_per_hall": 6,
}

NORMAL_SETTINGS = {
    "cooldown": 60,  # минут в обычном режиме
    "daily_limit": 10,
    "compensation_per_hall": 3,
}
