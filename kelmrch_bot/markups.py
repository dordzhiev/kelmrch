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
    r = types.InlineKeyboardMarkup(None, 2).add(
        *(
            types.InlineKeyboardButton(translation.word, callback_data=similar_word_factory.new(translation.id))
            for translation in translations
        )
    )
    r.row(
        types.InlineKeyboardButton(
            'Использовать обратный поиск', callback_data=reversed_translation_factory.new(word, 0))
    )
    return r


def reversed_translations_markup(translations: list[Translation], word, prev_page=None, next_page=None):
    r = types.InlineKeyboardMarkup(None, 2)
    if prev_page is not None:
        r.row(
            types.InlineKeyboardButton('‹ Назад', callback_data=reversed_translation_factory.new(word, prev_page))
        )
    r.add(
        *(
            types.InlineKeyboardButton(translation.word, callback_data=similar_word_factory.new(translation.id))
            for translation in translations
        )
    )
    if next_page is not None:
        r.row(
            types.InlineKeyboardButton('Дальше ›', callback_data=reversed_translation_factory.new(word, next_page))
        )
    return r
