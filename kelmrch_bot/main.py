from telebot import TeleBot

from config import config
from kelmrch_bot.handlers import import_handlers
from kelmrch_bot.filters import import_filters

bot = TeleBot(config.tgbot.token, 'HTML', num_threads=4)
import_handlers(bot)
import_filters(bot)
