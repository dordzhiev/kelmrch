import decimal
import re
from dataclasses import dataclass

import psycopg2
from psycopg2 import extras
from telebot import TeleBot, custom_filters, types

from config import load_config


@dataclass
class Translation:
    id: int
    vocabulary: chr
    word: str
    translation: str
    sml: decimal = None
    reference: str = None


config = load_config()

bot = TeleBot(config.tgbot.token, 'HTML')
bot.add_custom_filter(custom_filters.TextMatchFilter())

con = psycopg2.connect(
    f"dbname={config.database.dbname} "
    f"user={config.database.user} "
    f"password={config.database.password}"
)
cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


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


def translations_markup(translations: list[Translation]):
    return types.InlineKeyboardMarkup(None, 2).add(
        *(
            types.InlineKeyboardButton(translation.word, callback_data=translation.id)
            for translation in translations
        )
    )


def get_russian_translations(word, max_offset, query_offset):
    cur.execute('''
    SELECT 
        aw.id,
        vocabulary,
        word,
        STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation,
        strict_word_similarity (word, %s) as sml
    FROM all_words aw INNER JOIN all_translations at2
    ON aw.id = aw_id
    WHERE vocabulary = 'r' AND word %% %s
    GROUP BY aw.id, vocabulary, word
    ORDER BY sml DESC, id LIMIT %s OFFSET %s
    ''', (word, word, max_offset, query_offset))
    return [Translation(**entity) for entity in cur.fetchall()]


def get_kalmyk_translations(word, max_offset, query_offset):
    cur.execute('''
    SELECT
        aw.id,
        vocabulary,
        word,
        STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation,
        GREATEST ( strict_word_similarity (word, %s), strict_word_similarity (alias, %s) ) as sml
    FROM all_words aw
    INNER JOIN all_translations at2
    ON aw.id = aw_id
    LEFT JOIN cyrillic_aliases ca
    ON aw.id = ca.id
    WHERE vocabulary = 'k' AND (word %% %s OR alias %% %s)
    GROUP BY aw.id, vocabulary, word, alias
    ORDER BY sml DESC, id LIMIT %s OFFSET %s
    ''', (word, word, word, word, max_offset, query_offset))
    return [Translation(**entity) for entity in cur.fetchall()]


def get_translations(word, max_offset, query_offset) -> [Translation]:
    cur.execute('''
    SELECT
        aw.id,
        vocabulary,
        word,
        STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation,
        GREATEST ( strict_word_similarity (word, %s), strict_word_similarity (alias, %s) ) as sml
    FROM all_words aw INNER JOIN all_translations at2
    ON aw.id = aw_id
    LEFT JOIN cyrillic_aliases ca
    ON aw.id = ca.id
    WHERE word %% %s or alias %% %s
    GROUP BY aw.id, vocabulary, word, alias
    ORDER BY sml DESC, vocabulary, id LIMIT %s OFFSET %s
    ''', (word, word, word, word, max_offset, query_offset))
    return [Translation(**entity) for entity in cur.fetchall()]


def get_by_id(_id):
    cur.execute(
        '''
        SELECT
            aw.id,
            vocabulary,
            word,
            STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation
        FROM all_words aw INNER JOIN all_translations at2
        ON aw.id = aw_id
        WHERE aw.id = %s
        GROUP BY aw.id, vocabulary, word
        ''',
        (_id,)
    )
    return [Translation(**entity) for entity in cur.fetchall()]


def render_results(translations: list[Translation]):
    return [
        types.InlineQueryResultArticle(
            translation.id,
            translation.word,
            types.InputTextMessageContent(
                f'<b>{translation.word}</b>\n{translation.translation}',
            ),
            description=re.sub(r'<.+?>', '', translation.translation)
        ) for translation in translations
    ]


@bot.message_handler(['start'])
def start_handler(message: types.Message):
    bot.reply_to(
        message,
        'Отправьте слово, чтобы получить перевод.',
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(['help'])
def start_handler(message: types.Message):
    bot.reply_to(
        message,
        'Отправьте слово, чтобы получить перевод.\n\n'
        'Также данный бот можно использовать в любом чате, просто укажите ник бота и начните вводить.',
        reply_markup=translate_markup()
    )


@bot.message_handler(content_types=['text'])
def translate_handler(message: types.Message):
    if message.via_bot:
        return
    if len(message.text) > 30:
        bot.reply_to(message, 'Превышен лимит строки.')
        return
    r = get_translations(message.text, 1, 0)
    text = 'К сожалению, совпадений в словарях не найдено.'
    if r:
        translation = r[0]
        if translation.sml == 1:
            bot.send_message(
                message.chat.id,
                f'<b>{translation.word}</b>\n{translation.translation}',
            )
        else:
            text += '\n\nВозможно вы имели ввиду:'
            translations = get_translations(message.text, 6, 0)
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=translations_markup(translations)
            )
    else:
        bot.send_message(message.chat.id, text)


@bot.callback_query_handler(func=None)
def similar_word_handler(callback: types.CallbackQuery):
    translations = get_by_id(int(callback.data))
    if translations:
        translation = translations[0]
        bot.edit_message_text(
            f'<b>{translation.word}</b>\n{translation.translation}',
            callback.message.chat.id,
            callback.message.id,
        )
    else:
        bot.answer_callback_query(callback.id, 'Ошибка!')


@bot.inline_handler(lambda x: True)
def inline_handler(inline_query: types.InlineQuery):
    query_offset = int(inline_query.offset) if inline_query.offset else 0
    max_offset = 15
    new_offset = None
    translations = None
    if inline_query.query and not re.match(r'(k|к):$', inline_query.query) \
            and not re.match(r'(r|р):$', inline_query.query):
        if len(inline_query.query) > 30:
            r = [
                types.InlineQueryResultArticle(
                    0, 'Превышен лимит строки',
                    types.InputTextMessageContent(
                        '<b>Ошибка</b>/nПревышен лимит строки',
                        'HTML'
                    ),
                    description=''
                )
            ]
        elif re.match(r'k|к:', inline_query.query):
            query = inline_query.query[2:]
            translations = get_kalmyk_translations(query, max_offset, query_offset)
            r = render_results(translations)
        elif re.match(r'r|р:', inline_query.query):
            query = inline_query.query[2:]
            translations = get_russian_translations(query, max_offset, query_offset)
            r = render_results(translations)
        else:
            translations = get_translations(inline_query.query, max_offset, query_offset)
            r = render_results(translations)
    else:
        r = [
            types.InlineQueryResultArticle(
                0, 'Начните вводить',
                types.InputTextMessageContent(
                    'В боте используется <a href="https://core.telegram.org/bots/inline">inline mode</a>. Для того, чтобы перевести слово, в текстовом поле введите ник бота: <code>@kelmrch_bot </code>, затем начните вводить слово.',
                ),
                description=''
            )
        ]
    if translations:
        if len(translations) == max_offset:
            new_offset = query_offset + max_offset
        else:
            new_offset = query_offset + len(translations)
    bot.answer_inline_query(str(inline_query.id), r, 0, False, new_offset)


if __name__ == '__main__':
    bot.infinity_polling(skip_pending=True)
