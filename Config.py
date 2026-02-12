from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DIR = Path(__file__).absolute().parent.parent.parent
BOT_DIR = Path(__file__).absolute().parent.parent


class EnvBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class BotSettings(EnvBaseSettings):
    BOT_TOKEN: str


class DBSettings(EnvBaseSettings):
    @property
    def database_path(self) -> str: 
        return "/home/timur/Documents/Languages/Python/Freelance/tutikovstanislav1/GymLegend/gym_legend.db"


class GameSettings(EnvBaseSettings):
    # ==============================
    # КОНСТАНТЫ ОБОРУДОВАНИЯ (20 УРОВНЕЙ)
    # ==============================

    DUMBBELL_LEVELS: dict = {
        1: {"name": "Гантеля 1кг", "price": 0, "weight": "1кг", "income_per_use": 1, "power_per_use": 1, "display_gap": True},
        2: {"name": "Гантеля 2кг", "price": 10, "weight": "2кг", "income_per_use": 2, "power_per_use": 2, "display_gap": True},
        3: {"name": "Гантеля 3кг", "price": 20, "weight": "3кг", "income_per_use": 3, "power_per_use": 3, "display_gap": True},
        4: {"name": "Гантеля 4кг", "price": 35, "weight": "4кг", "income_per_use": 4, "power_per_use": 4, "display_gap": True},
        5: {"name": "Гантеля 5кг", "price": 75, "weight": "5кг", "income_per_use": 5, "power_per_use": 5, "display_gap": True},
        6: {"name": "Гантеля 6кг", "price": 110, "weight": "6кг", "income_per_use": 7, "power_per_use": 6, "display_gap": True},
        7: {"name": "Гантеля 7кг", "price": 145, "weight": "7кг", "income_per_use": 9, "power_per_use": 7, "display_gap": True},
        8: {"name": "Гантеля 8кг", "price": 200, "weight": "8кг", "income_per_use": 10, "power_per_use": 8, "display_gap": True},
        9: {"name": "Гантеля 9кг", "price": 250, "weight": "9кг", "income_per_use": 12, "power_per_use": 9, "display_gap": True},
        10: {"name": "Гантеля 10кг", "price": 275, "weight": "10кг", "income_per_use": 13, "power_per_use": 10, "display_gap": True},
        11: {"name": "Штанга 10кг", "price": 350, "weight": "10кг", "income_per_use": 15, "power_per_use": 15, "display_gap": True},
        12: {"name": "Штанга 12.5кг", "price": 400, "weight": "12.5кг", "income_per_use": 16, "power_per_use": 17, "display_gap": True},
        13: {"name": "Штанга 15кг", "price": 450, "weight": "15кг", "income_per_use": 18, "power_per_use": 19, "display_gap": True},
        14: {"name": "Штанга 17.5кг", "price": 650, "weight": "17.5кг", "income_per_use": 21, "power_per_use": 23, "display_gap": True},
        15: {"name": "Штанга 20кг", "price": 750, "weight": "20кг", "income_per_use": 23, "power_per_use": 25, "display_gap": True},
        16: {"name": "Становая тяга 40кг", "price": 1000, "weight": "40кг", "income_per_use": 28, "power_per_use": 40, "display_gap": True},
        17: {"name": "Становая тяга 60кг", "price": 1250, "weight": "60кг", "income_per_use": 30, "power_per_use": 60, "display_gap": True},
        18: {"name": "Становая тяга 80кг", "price": 1500, "weight": "80кг", "income_per_use": 35, "power_per_use": 70, "display_gap": True},
        19: {"name": "Становая тяга 100кг", "price": 2000, "weight": "100кг", "income_per_use": 50, "power_per_use": 100, "display_gap": True},
        20: {"name": "Становая тяга 120кг", "price": 2500, "weight": "120кг", "income_per_use": 75, "power_per_use": 125, "display_gap": True}
    }

    DUMBBELL_COOLDOWN: int = 60
    
    # Разделитель между гантелями при выводе
    DUMBBELL_DISPLAY_SEPARATOR: str = "\n\n"

    # ==============================
    # СИСТЕМА ПРОВЕРОК И ЗАЩИТЫ
    # ==============================
    
    # Уровни проверяющих
    INSPECTOR_LEVELS: dict = {
        1: {"price": 3, "min_damage": 0, "max_damage": 1},
        2: {"price": 6, "min_damage": 1, "max_damage": 2},
        3: {"price": 15, "min_damage": 3, "max_damage": 5},
        4: {"price": 50, "min_damage": 5, "max_damage": 7},
        5: {"price": 100, "min_damage": 8, "max_damage": 10},
    }
    
    # Уровни защиты
    PROTECTION_LEVELS: dict = {
        1: {"name": "Привести все залы в порядок", "price": 35, "duration": 15, "chance": 10, "max_inspector_level": 2},
        2: {"name": "Слухи о подкупе", "price": 75, "duration": 30, "chance": 15, "max_inspector_level": 3},
        3: {"name": "У нас все четко", "price": 100, "duration": 30, "chance": 20, "max_inspector_level": 4},
        4: {"name": "Заплатить больше другого", "price": 175, "duration": 60, "chance": 40, "max_inspector_level": 5},
        5: {"name": "Свои люди в прокуратуре", "price": 350, "duration": 60, "chance": 100, "max_inspector_level": 5},
    }
    
    # Настройки режимов
    INSPECTION_TIME_SETTINGS: dict = {
        "cooldown": 30,  # минут в режиме "Время проверок"
        "daily_limit": 24,
        "compensation_per_hall": 6,
    }

    NORMAL_SETTINGS: dict = {
        "cooldown": 60,  # минут в обычном режиме
        "daily_limit": 10,
        "compensation_per_hall": 3,
    }

    # ==============================
    # КОНСТАНТЫ КЛАНОВ
    # ==============================

    CLAN_CREATE_COST: int = 350
    CLAN_UPGRADE_BASE_COST: int = 100
    CLAN_TRANSFER_COST: int = 500  # Стоимость передачи клана
    CLAN_MAX_LEVEL: int = 100  # Максимальный уровень клана

    # ==============================
    # АДМИН КОНСТАНТЫ
    # ==============================

    ADMIN_USERS: list[int] = [1, 322615766, 768764050]


class Settings(BotSettings, DBSettings, GameSettings):
    DEBUG: bool = False


settings = Settings()
