from telebot import types

from kelmrch_bot.dto import Translation
from kelmrch_bot.filters import similar_word_factory, reversed_translation_factory


def translate_markup():
    return types.InlineKeyboardMarkup(None, 1).add(
        *(
            types.InlineKeyboardButton(
                'С обоих языков',
                switch_inline_query_current_chat=''
            ),
            types.InlineKeyboardButton(
                'С калмыцкого',
                switch_inline_query_current_chat='k:'
            ),
            types.InlineKeyboardButton(
                'С русского',
                switch_inline_query_current_chat='r:'
            ),
        )
    )


def translations_markup(translations: list[Translation], word):
    return types.InlineKeyboardMarkup(None, 2).add(
        *(
            types.InlineKeyboardButton(translation.word, callback_data=similar_word_factory.new(translation.id))
            for translation in translations
        ),
        types.InlineKeyboardButton('Использовать обратный поиск', callback_data=reversed_translation_factory.new(word))
    )
