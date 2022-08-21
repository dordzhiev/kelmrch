import re

from telebot import types

from kelmrch_bot.dto import Translation


def render_results(translations: list[Translation]):
    return [
        types.InlineQueryResultArticle(
            translation.id,
            translation.word,
            types.InputTextMessageContent(
                f'<b>{translation.word}</b>\n{translation.translation}',
                'HTML',
            ),
            description=re.sub(r'<.+?>', '', translation.translation)
        ) for translation in translations
    ]
