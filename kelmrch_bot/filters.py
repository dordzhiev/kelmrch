from telebot import TeleBot, types, custom_filters, callback_data

similar_word_factory = callback_data.CallbackData('word_id', prefix='similar_word')
reversed_translation_factory = callback_data.CallbackData('word', 'page', prefix='reversed_translation')


class CustomCallbackFilter(custom_filters.AdvancedCustomFilter):
    key = 'config'

    def check(self, call: types.CallbackQuery, config: callback_data.CallbackDataFilter):
        return config.check(query=call)


def import_filters(bot: TeleBot):
    bot.add_custom_filter(custom_filters.TextMatchFilter())
    bot.add_custom_filter(CustomCallbackFilter())
