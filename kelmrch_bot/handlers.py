import re

from telebot import types, TeleBot

from kelmrch_bot.repository import repository
from kelmrch_bot.utils import render_results
from kelmrch_bot.markups import translate_markup, translations_markup, reversed_translations_markup, no_results_markup
from kelmrch_bot.filters import similar_word_factory, reversed_translation_factory


def start_handler(message: types.Message, bot: TeleBot):
    bot.reply_to(
        message,
        'Отправьте слово, чтобы получить перевод.',
        reply_markup=types.ReplyKeyboardRemove()
    )


def help_handler(message: types.Message, bot: TeleBot):
    bot.reply_to(
        message,
        'Отправьте слово, чтобы получить перевод.\n\n'
        'Также данный бот можно использовать в любом чате, просто укажите ник бота и начните вводить.',
        reply_markup=translate_markup()
    )


def translate_handler(message: types.Message, bot: TeleBot):
    if message.via_bot:
        return
    if len(message.text) > 30:
        bot.reply_to(message, 'Превышен лимит строки.')
        return
    text = 'К сожалению, совпадений в словарях не найдено.'
    result = repository.get_translations(message.text, 1, 0)
    if result:
        translation = result[0]
        if translation.sml == 1:
            bot.send_message(
                message.chat.id,
                f'<b>{translation.word}</b>\n{translation.translation}',
            )
        else:
            similar_results = repository.get_translations(message.text, 6, 0)
            if similar_results:
                text += '\n\nВозможно вы имели ввиду:'
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=translations_markup(similar_results, message.text)
            )
    else:
        bot.send_message(message.chat.id, text, reply_markup=no_results_markup(message.text))


def similar_word_handler(callback: types.CallbackQuery, bot: TeleBot):
    data = similar_word_factory.parse(callback.data)
    word_id = int(data['word_id'])
    translation = repository.get_by_id(word_id)
    if translation:
        bot.send_message(callback.message.chat.id, f'<b>{translation.word}</b>\n{translation.translation}')
    else:
        bot.answer_callback_query(callback.id, 'Ошибка!')


def reversed_translation_handler(callback: types.CallbackQuery, bot: TeleBot):
    data = reversed_translation_factory.parse(callback.data)

    word = data['word']
    page = int(data['page'])

    word_count = 6
    limit = 7
    offset = word_count * page

    prev_page = None
    next_page = None

    translations = repository.get_reversed_translations(word, limit, offset)

    if translations:
        if page > 0:
            prev_page = page - 1

        if len(translations) == limit:
            next_page = page + 1

        bot.edit_message_reply_markup(
            callback.message.chat.id,
            callback.message.message_id, None,
            reversed_translations_markup(translations[:word_count], word, prev_page, next_page)
        )

    else:
        bot.answer_callback_query(callback.id, 'Результатов не найдено. 😔')


def inline_handler(inline_query: types.InlineQuery, bot: TeleBot):
    query_offset = int(inline_query.offset) if inline_query.offset else 0
    max_offset = 15
    new_offset = None
    translations = None
    if inline_query.query and not re.match(r'(k|к|r|р):$', inline_query.query):
        if len(inline_query.query) > 30:
            r = [
                types.InlineQueryResultArticle(
                    0, 'Превышен лимит строки',
                    types.InputTextMessageContent(
                        '<b>Ошибка</b>\nПревышен лимит строки',
                        'HTML'
                    ),
                    description=''
                )
            ]
        elif re.match(r'k|к:', inline_query.query):
            query = inline_query.query[2:]
            translations = repository.get_kalmyk_translations(query, max_offset, query_offset)
            r = render_results(translations)
        elif re.match(r'r|р:', inline_query.query):
            query = inline_query.query[2:]
            translations = repository.get_russian_translations(query, max_offset, query_offset)
            r = render_results(translations)
        else:
            translations = repository.get_translations(inline_query.query, max_offset, query_offset)
            r = render_results(translations)
    else:
        r = [
            types.InlineQueryResultArticle(
                0, 'Начните вводить',
                types.InputTextMessageContent(
                    'В боте используется <a href="https://core.telegram.org/bots/inline">inline mode</a>. Для того, чтобы перевести слово, в текстовом поле введите ник бота: <code>@kelmrch_bot </code>, затем начните вводить слово.',
                    'HTML'
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


def import_handlers(bot: TeleBot):
    bot.register_message_handler(
        start_handler, None, ['start'], pass_bot=True)
    bot.register_message_handler(
        help_handler, None, ['help'], pass_bot=True)
    bot.register_message_handler(
        translate_handler, ['text'], pass_bot=True)
    bot.register_callback_query_handler(
        similar_word_handler, None, pass_bot=True, config=similar_word_factory.filter())
    bot.register_callback_query_handler(
        reversed_translation_handler, None, pass_bot=True, config=reversed_translation_factory.filter())
    bot.register_inline_handler(
        inline_handler, None, pass_bot=True)
