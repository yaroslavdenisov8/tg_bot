import logging
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ConversationHandler
from telegram import ReplyKeyboardMarkup
from config import BOT_TOKEN
import sqlite3
import datetime

# Запускаем логгирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Подключение к БД
con = sqlite3.connect("tasks.db")
cur = con.cursor()

date = None
time = None


def delete_irrelevant_tasks():
    now = str(datetime.datetime.now())[: -10]
    cur.execute(f"""DELETE FROM tasks WHERE time < '{now}'""").fetchall()
    con.commit()


def check_datetime(dt):
    try:
        y = int(dt[: 4])
        m = int(dt[5: 7])
        d = int(dt[8: 10])

        h = int(dt[11: 13])
        mm = int(dt[15:])

        datetime.datetime(y, m, d, h, mm)
        return True

    except ValueError:
        return False


async def start(update, context):
    reply_keyboard = [['/book', '/delete'],
                      ['/tasks', '/clean']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    await update.message.reply_text("Привет! Вот что я умею:\n"
                                    "Зарланировать - /book\n"
                                    "Удалить задачу - /delete\n"
                                    "Посмотреть список дел - /tasks\n"
                                    "Очистить список дел - /clean",
                                    reply_markup=markup)


async def base_response(update, context):
    reply_keyboard = [['/book', '/delete'],
                      ['/tasks', '/clean']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    
    await update.message.reply_text("Я вас не понимаю, пожалуйста, используйте команды", reply_markup=markup)


async def book(update, context):
    await update.message.reply_text('На какую дату вы хотите запланировать задачу?(Формат yy.mm.dd)')
    return 1


async def book_response1(update, context):
    global date
    date = '20' + update.message.text
    date = date.replace('.', '-')
    await update.message.reply_text('На какое время вы хотите запланировать задачу? (Формат HH:MM)')
    return 2


async def book_response2(update, context):
    global time
    time = update.message.text
    await update.message.reply_text('Что вы хотите запланировать?')
    return 3


async def book_response3(update, context):
    global date, time
    dt = date + ' ' + time

    if check_datetime(dt):
        cur.execute(f"""INSERT INTO tasks(task, time) 
                        VALUES ('{update.message.text}', '{dt}')""").fetchall()
        con.commit()

        await update.message.reply_text('Задача запланирована')
        return ConversationHandler.END
    else:
        await update.message.reply_text('Пожалуйста, вводите корректные данные')
        return ConversationHandler.END


async def delete(update, context):
    response = ''
    result = cur.execute(f"""SELECT * FROM tasks""").fetchall()

    if result:
        for i in result:
            dt = i[2].replace('-', '.')
            response += f'{i[1]} - {dt[2:]}\n'

        await update.message.reply_text('Укажите время задачи, которую хотите удалить')
        await update.message.reply_text(response)
        return 1
    else:
        await update.message.reply_text('У вас пока нет дел')
        return ConversationHandler.END


async def delete_response(update, context):
    dt = '20' + update.message.text.strip(' ').replace('.', '-')

    delete_irrelevant_tasks()
    res = cur.execute(f"""DELETE FROM tasks WHERE time = '{dt}'""").fetchall()
    con.commit()

    if res:
        await update.message.reply_text('Задача удалена')
    else:
        await update.message.reply_text('На это время задачи отсутствуют')
    return ConversationHandler.END


async def tasks(update, context):
    response = ''
    delete_irrelevant_tasks()
    result = cur.execute(f"""SELECT * FROM tasks""").fetchall()

    if result:
        n = 1
        for i in result:
            dt = i[2].replace('-', '.')
            response += f'{n}) {i[1]} - {dt[2:]}\n'
            n += 1

        await update.message.reply_text(response)
    else:
        await update.message.reply_text('У вас пока нет дел')


async def clean(update, context):
    cur.execute(f"""DELETE FROM tasks""").fetchall()
    con.commit()
    await update.message.reply_text('Все задачи удалены')


async def stop(update, context):
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    book_handler = ConversationHandler(
        entry_points=[CommandHandler('book', book)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_response1)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_response2)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_response3)]
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    delete_handler = ConversationHandler(
        entry_points=[CommandHandler('delete', delete)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_response)],
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(book_handler)
    application.add_handler(delete_handler)
    application.add_handler(CommandHandler("tasks", tasks))
    application.add_handler(CommandHandler("clean", clean))
    application.add_handler(MessageHandler(filters.TEXT, base_response))

    application.run_polling()


if __name__ == '__main__':
    main()
