from dataclasses import dataclass
from configparser import ConfigParser
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
config_path = os.path.join(BASE_DIR, 'config.ini')


@dataclass
class Database:
    dbname: str
    user: str
    password: str


@dataclass
class TgBot:
    token: str


@dataclass
class Config:
    database: Database
    tgbot: TgBot


def load_config(path: str = config_path):
    config = ConfigParser()
    config.read(path)

    return Config(
        tgbot=TgBot(**config['bot']),
        database=Database(**config["db"]),
    )
