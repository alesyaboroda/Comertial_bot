import sqlite3
import os
import logging
import sqlite3
import database
from uuid import uuid4
from telegram import __version__ as TG_VER, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineQueryResultArticle, \
    InlineKeyboardButton, InlineKeyboardMarkup, InputTextMessageContent, Update, CallbackQuery, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes, InlineQueryHandler, MessageHandler, filters, \
    ConversationHandler, CallbackQueryHandler, CallbackDataCache, PreCheckoutQueryHandler

token = "Bot token"
PAYMENT_PROVIDER_TOKEN = "Merchant id"

# Stages
START_ROUTES, END_ROUTES = range(2)
# Callback data
CATEGORY_1, CATEGORY_2, CATEGORY_3, CATEGORY_4, CATEGORY_5, PAGE_FORWARD, PAGE_BACKWARD, SEARCH, EIGHT, DONE, \
    CONFIRMATION, CONFIRMATION_PAID, DONE_PAID, START_OVER = range(14)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    text = ("Здравствуйте. Меня зовут ЛиМА. Я телеграмм бот который поможет вам найти нужный образец заявления в суд."
            "В настоящее время у меня есть заявления по гражданскому, семейному и наследственному праву, и вы можете"
            "заказать отдельно заявление по любой отрасли права. Я постоянно развиваюсь и моя база пополняется"
            "каждый день.")
    buttons = [
        [
            InlineKeyboardButton(text="Общие заявления по ГПК РФ", callback_data=str(CATEGORY_1))
        ],
        [
            InlineKeyboardButton(text="Заявления по семейным спорам", callback_data=str(CATEGORY_2))
        ],
        [
            InlineKeyboardButton(text="Заявления по наследственным спорам", callback_data=str(CATEGORY_3))
        ],
        [
            InlineKeyboardButton(text="Заявления по трудовым спорам", callback_data=str(CATEGORY_4))
        ],
        [
            InlineKeyboardButton(text="Другое", callback_data=str(CATEGORY_5))
        ],
        [
            InlineKeyboardButton(text="Отмена", callback_data=str(DONE)),
            InlineKeyboardButton(text="Поиск", callback_data=str(FIND))
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    # If we're starting over we don't need to send a new message
    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = False
    return START_ROUTES


async def make_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show new choice of buttons"""
    callback_data = update.callback_query.data
    if callback_data == '0':
        chosen_category = 'Общие заявления по ГПК РФ'
    elif callback_data == '1':
        chosen_category = 'Заявления по семейным спорам'
    elif callback_data == '2':
        chosen_category = 'Заявления по наследственным спорам'
    elif callback_data == '3':
        chosen_category = 'Заявления по трудовым спорам'
    elif callback_data == '4':
        chosen_category = 'Другое'
    else:
        return ERROR
    print(update.callback_query.data)
    query = update.callback_query
    await query.answer()
    data = context.user_data
    if 'pages' in data.keys():
        pages = context.user_data["pages"]
    else:
        pages = button_maker_delux(database.get_list_of_files_in_category(chosen_category))
        context.user_data["pages"] = pages
    if 'page' in data.keys():
        page = context.user_data['page']
    else:
        page = 0
        context.user_data["page"] = page
    keyboard = pages[page]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Выбери файл для отправки, страница " + str(page + 1), reply_markup=reply_markup)
    context.user_data[START_OVER] = True
    return SEARCH


async def page_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = context.user_data
    pages = data["pages"]
    page = data['page'] + 1
    data['page'] = page
    keyboard = pages[page]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Выбери файл для отправки, страница " + str(page + 1), reply_markup=reply_markup)
    return SEARCH


async def page_backward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = context.user_data
    pages = data["pages"]
    page = data['page'] - 1
    data['page'] = page
    keyboard = pages[page]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="выбери файл для отправки, страница " + str(page + 1), reply_markup=reply_markup)
    return SEARCH


async def free_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "Вы уверены что хотите скачать " + str(query.data)
    context.user_data['chosen file'] = str(query.data)
    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data=str(DONE)),
            InlineKeyboardButton(text="Нет", callback_data=str(CATEGORY_1)),
        ]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    return CONFIRMATION


async def sending_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    file = str(context.user_data['chosen file'])
    document = open('Files/' + file, 'rb')
    chat_id = update.effective_chat.id
    await query.answer()
    await query.edit_message_text(text='Файл "' + (context.user_data['chosen file']) + '" отправлен.')
    await context.bot.send_document(chat_id, document)
    return ConversationHandler.END


async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    path = r'Files/' + str(context.user_data['chosen file'])
    document = open(path, 'rb')
    chat_id = update.effective_chat.id
    title = str(context.user_data['chosen file'])
    description = 'Для скачки файла нажмите на кнопку "Заплатить"'
    # select a payload just for you to recognize its the donation from your bot
    payload = "Custom-Payload"
    currency = "RUB"
    price = int(context.user_data['price'])
    # price * 100 so as to include 2 decimal points
    prices = [LabeledPrice("Цена", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    await context.bot.send_invoice(
        chat_id, title, description, payload, PAYMENT_PROVIDER_TOKEN, currency, prices
    )


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    path = r'Files/' + str(context.user_data['chosen file'])
    document = open(path, 'rb')
    chat_id = update.effective_chat.id
    await update.message.reply_text("Файл " + (context.user_data['chosen file']) + " отправлен")
    await context.bot.send_document(chat_id, document)
    return ConversationHandler.END


async def paid_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    name = str(query.data)
    context.user_data['chosen file'] = name
    context.user_data['price'] = database.get_price(name)
    text = "Вы уверены что хотите купить " + name + " за " + context.user_data['price'] + "?"
    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data=str(DONE_PAID)),
            InlineKeyboardButton(text="Нет", callback_data=str(CATEGORY_2)),
        ]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    context.user_data[START_OVER] = False
    return CONFIRMATION_PAID


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != "Custom-Payload":
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Bye!")
    context.user_data.clear()
    return ConversationHandler.END


def button_maker_delux(file_list):
    length = len(file_list)
    pages = []
    buttons = []
    for file in file_list:
        buttons.append([InlineKeyboardButton(file, callback_data=str(file))])
        if len(buttons) == 4 or (len(buttons) == length and len(buttons) != 0):
            if len(buttons) < length:
                buttons.append([InlineKeyboardButton('>>', callback_data=PAGE_FORWARD)])
            if len(pages) > 0:
                buttons.append([InlineKeyboardButton('<<', callback_data=PAGE_BACKWARD)])
            buttons.append([InlineKeyboardButton('Отмена', callback_data=DONE)])
            length -= 4
            pages.append(buttons)
            buttons = []
    return pages


# print(database.get_list_of_files_in_category())
# database.insert('хуй', 'категория', 1)
# print(database.get_list_of_files_in_category())


def main() -> None:
    # Create the Application and pass it your bot token.
    application = Application.builder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(make_keyboard, pattern="^" + str(CATEGORY_1) + "$"),
                CallbackQueryHandler(make_keyboard, pattern="^" + str(CATEGORY_2) + "$"),
                CallbackQueryHandler(make_keyboard, pattern="^" + str(CATEGORY_3) + "$"),
                CallbackQueryHandler(make_keyboard, pattern="^" + str(CATEGORY_4) + "$"),
                CallbackQueryHandler(make_keyboard, pattern="^" + str(CATEGORY_5) + "$"),
                CallbackQueryHandler(cancel, pattern="^" + str(DONE) + "$")
            ],
            SEARCH: [
                CallbackQueryHandler(page_forward, pattern="^" + str(PAGE_FORWARD) + "$"),
                CallbackQueryHandler(page_backward, pattern="^" + str(PAGE_BACKWARD) + "$"),
                CallbackQueryHandler(start, pattern="^" + str(DONE) + "$"),
                CallbackQueryHandler(paid_confirm),
            ],
            CONFIRMATION_PAID: [
                CallbackQueryHandler(send_invoice, pattern="^" + str(DONE_PAID) + "$"),
                CallbackQueryHandler(make_keyboard, pattern="^" + str(CATEGORY_2) + "$"),
                MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
