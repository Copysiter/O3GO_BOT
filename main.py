import os, sys

import sqlite3
import time


from threading import Thread
from datetime import datetime, timedelta, timezone

import telebot
from telebot import types

from pony.orm import *
from db import *

import pandas as pd

from config import *

from scheduler import start_scheduler

from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

import calendar

'''
import pytz

rus = pytz.timezone('Europe/Samara')
curtime =rus.localize(datetime.now())
print(curtime)
'''

#con = sqlite3.connect('worktime.db')
#cur = con.cursor()

# Creates a unique calendar
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_callback = CallbackData('calendar_from', 'action', 'year', 'month', 'day', 'temp')
#calendar_callback_to = CallbackData('calendar_to', 'action', 'year', 'month', 'day')

bot = telebot.TeleBot(TELEBOT_BOT_TOKEN)


def translate_date(date):
    month_dict = {
        'January': 'Января',
        'February': 'Февраля',
        'March': 'Марта',
        'April': 'Апреля',
        'May': 'Мая',
        'June': 'Июня',
        'July': 'Июля',
        'August': 'Августа',
        'September': 'Сентября',
        'October': 'Октября',
        'November': 'Ноября',
        'December': 'Декабря',
        'Jan': 'Янв',
        'Feb': 'Фев',
        'Mar': 'Мар',
        'Apr': 'Апр',
        'May': 'Май',
        'Jun': 'Июн',
        'Jul': 'Июл',
        'Aug': 'Авг',
        'Sep': 'Сен',
        'Oct': 'Окт',
        'Nov': 'Ноя',
        'Dec': 'Дек'
    }
    for key, value in month_dict.items():
        date = date.replace(key, value)
    return date


def reply_keyboard(user):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row_width = 2
    markup_buttons = []
    reports = user.reports.select(lambda x: x.end_ts is None)[:1]
    if len(reports) > 0:
        markup_buttons.append(types.KeyboardButton('🍺 Ушел'))
    else:
        markup_buttons.append(types.KeyboardButton('🛠 Пришел'))
    markup_buttons.append(types.KeyboardButton('📁 Статистика'))
    if user.is_superuser:
        markup_buttons.append(types.KeyboardButton('👥 Пользователи'))
    markup.add(*markup_buttons)
    return markup


def user_info(user):
    return (f'User ID: {user.ext_id}\n' +
            f'Username: {user.username}\n' +
            f'First name: {user.first_name}\n' +
            f'Last name: {user.last_name}')

def user_keyboard(user):
    markup=types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            'Заблокировать' if user.is_active else 'Активировать',
            callback_data=f'USER:ACTIVATE:{user.id}'
        ),
        types.InlineKeyboardButton(
            'Удалить из базы', callback_data=f'USER:REMOVE:{user.id}'
        )
    )
    return markup


def export_report(user, ts_from, ts_to):
    chat_id = user.ext_id
    path = f'{os.path.dirname(os.path.abspath(__file__))}/export/{ts_from}_{ts_to}_{round(time.time())}.xlsx'
    writer = pd.ExcelWriter(path, engine='xlsxwriter')
    for user in User.select(lambda x: (x.id == user.id or (user.is_superuser and x.is_active))):
        name = [c for c in [user.first_name, user.last_name, user.username, user.ext_id] if c][0]
        df = pd.DataFrame(index=['date', 'begin', 'end', 'hours', 'chat_id', 'firt_name', 'last_name', 'username'])
        for report in user.reports.select(lambda x: x.end_ts and x.begin_ts.date() >= datetime.strptime(ts_from, '%Y-%m-%d').date() and x.begin_ts.date() <= datetime.strptime(ts_to, '%Y-%m-%d').date()):
            print(report.begin_ts.date())
            df[report.begin_ts] = [
                report.begin_ts.strftime('%d.%m.%Y'),
                report.begin_ts.strftime('%H:%M'),
                report.end_ts.strftime('%H:%M'),
                round((report.end_ts - report.begin_ts).seconds / 3600, 2),
                user.ext_id,
                user.first_name,
                user.last_name,
                user.username
            ]
        #with pd.ExcelWriter(path, engine='xlsxwriter') as writer:   
        df.T.reset_index(drop=True).to_excel(writer, sheet_name=name)
    writer.close()
    bot.send_document(chat_id, open(path, mode='rb'))


@bot.message_handler(commands=['start'])
def start_message(message):
    with db_session:
        user = User.get(lambda x: x.ext_id == message.from_user.id)
        #print(user.reports[:][0])
        if not user:
            user = User(
                ext_id = message.from_user.id,
                username = message.from_user.username,
                first_name = message.from_user.first_name,
                last_name = message.from_user.last_name,
                is_active = False,
                is_superuser = False
            )
            flush()
        name = [c for c in [user.first_name, user.last_name, user.username, user.ext_id] if c][0]
        if not user.is_active:
            text = f'💥 Приветствую Вас, <b>{name}</b>.\nВаш ID 622745113.\nДождитесь активации аккаунта.'
        else:
            text = f'💥 С возвращением, <b>{name}</b>.\nВаш ID 622745113.'
        bot.send_message(
            message.chat.id,
            text, parse_mode='HTML',
            reply_markup=(reply_keyboard(user) if user.is_active else False)
        )
        if not user.is_active:
            for superuser in User.select(lambda x: x.is_superuser)[:]:
                bot.send_message(
                    superuser.ext_id,
                    f'🔔 <b>Новый пользователь:</b>\n\n{user_info(user)}', parse_mode='HTML',
                    reply_markup=user_keyboard(user)
                )

@bot.message_handler(content_types='text')
def message_reply(message):
    #user  = get_user({'ext_id': message.from_user.id})
    now = datetime.fromtimestamp(
        message.date + 3600 * TIMEZONE_DELTA
    )
    with db_session:
        user = User.get(lambda x: x.ext_id == message.from_user.id)
        if user:

            if message.text == SUPER_USER_PSW:
                user.set(
                    is_active = True,
                    is_superuser = True
                )
                bot.send_message(
                    message.chat.id,
                    'Вы авторизоыаны в качестве администратора.', parse_mode='HTML',
                    reply_markup=reply_keyboard(user)
                )

            if user.is_active:

                if message.text == '🛠 Пришел':
                    # ts = datetime.fromtimestamp(
                    #    message.date,
                    #    timezone(timedelta(hours=TIMEZONE_DELTA))
                    # )
                    #reports = user.reports.select(lambda x: x.begin_ts.date() == now.date())[:1]
                    reports = user.reports.select(lambda x: True).order_by(lambda x: desc(x.begin_ts))[:1]
                    if len(reports) > 0 and reports[0].end_ts is None:
                        day = translate_date(reports[0].begin_ts.strftime('%d %B %Y'))
                        time = reports[0].begin_ts.strftime('%H:%M')
                        text = f'<b>{day}</b>:   Ты уже пришел в {time}'
                    else:
                        day = translate_date(now.strftime('%d %B %Y'))
                        time = now.strftime('%H:%M')
                        text = f'<b>{day}</b>:   Ты пришел в {time}'
                        report =  Reports(
                            user = user,
                            begin_ts = now
                        )
                    bot.send_message(
                        message.chat.id,
                        text, parse_mode='HTML',
                        reply_markup=reply_keyboard(user)
                    )

                if message.text == '🍺 Ушел':
                    #reports = user.reports.select(lambda x: x.begin_ts.date() == now.date())[:1]
                    reports = user.reports.select(lambda x: True).order_by(lambda x: desc(x.begin_ts))[:1]
                    if len(reports) > 0:
                        if reports[0].end_ts is None:
                            reports[0].set(
                                end_ts = now
                            )
                            day = translate_date(now.strftime('%d %B %Y'))
                            time = now.strftime('%H:%M')
                        else:
                            day = translate_date(reports[0].begin_ts.strftime('%d %B %Y'))
                            time = reports[0].begin_ts.strftime('%H:%M')
                        bot.send_message(
                            message.chat.id,
                            f'<b>{day}</b>:   Ты ушел в {time}', parse_mode='HTML',
                            reply_markup=reply_keyboard(user)
                        )
                    else:
                        bot.send_message(
                            message.chat.id,
                            'Ошибка:\nВас не было на работе',
                            reply_markup=reply_keyboard(user)
                        )

                if message.text == '📁 Статистика':
                    markup = calendar.create_calendar(
                        calendar_callback.prefix,
                        year=now.year,
                        month=now.month,
                        day=now.day
                    )
                    bot.send_message(message.chat.id, 'Выберите начальную дату:', reply_markup=markup)

                if message.text == '👥 Пользователи':
                    if user.is_superuser:
                        for user in User.select(lambda x: x.id != user.id):
                            bot.send_message(
                                message.chat.id,
                                user_info(user), parse_mode='HTML',
                                reply_markup=user_keyboard(user)
                            )
            else:
                bot.send_message(message.chat.id, '🔒 Ваш аккаунт не активен')                

@bot.callback_query_handler(
    func=lambda call: call.data.startswith('USER')
)
def callback_user(call: types.CallbackQuery):
    action, user_id = call.data.split(':')[1:]
    with db_session:
        user = User.get(lambda x: x.id == user_id)
        if user:
            if action == 'ACTIVATE':
                if user.is_active:
                    user.set(
                        is_active = False
                    ) 
                    bot.send_message(
                        user.ext_id,
                        '🔒 Ваш аккаунт звблокирован',
                        parse_mode='HTML',
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                    bot.edit_message_text(
                        chat_id = call.message.chat.id,
                        message_id = call.message.message_id,
                        text = '🔒 Пользователь звблокирован'
                    )
                else:
                    user.set(
                        is_active = True
                    ) 
                    bot.send_message(
                        user.ext_id,
                        '👍 Ваш аккаунт активирован',
                        parse_mode='HTML',
                        reply_markup=reply_keyboard(user)
                    )
                    bot.edit_message_text(
                        chat_id = call.message.chat.id,
                        message_id = call.message.message_id,
                        text = '👍 Пользователь активирован'
                    )

            if action == 'REMOVE':
                delete(x for x in Reports if x.user.id == user_id)
                user.delete()
                bot.send_message(
                    user.ext_id,
                    '🚫 Ваш аккаунт был удален', parse_mode='HTML',
                    reply_markup=types.ReplyKeyboardRemove()
                )
                bot.edit_message_text(
                    chat_id = call.message.chat.id,
                    message_id = call.message.message_id,
                    text = '🚫 Пользователь был удален'
                )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(calendar_callback.prefix)
)
def callback_stat(call: types.CallbackQuery):
    '''
    Обработка inline callback запросов
    :param call:
    :return:
    '''
    #print(call)
    #print(call.data)
    # At this point, we are sure that this calendar is ours. So we cut the line by the separator of our calendar
    name, action, year, month, day, temp = call.data.split(calendar_callback.sep)

    # Processing the calendar. Get either the date or None if the buttons are of a different type
    date = calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day, temp=temp
    )
    # There are additional steps. Let's say if the date DAY is selected, you can execute your code. I sent a message.
    if action == 'DAY':
        '''
        bot.send_message(
            chat_id=call.from_user.id,
            text=f'Начальная дата: {date.strftime('%d.%m.%Y')}',
            #reply_markup=types.ReplyKeyboardRemove(),
        )
        '''
        #calendar_callback_to = CallbackData('calendar_to', date.strftime('%d.%m.%Y'), 'action', 'year', 'month', 'day')
        if len(temp) > 0:
             with db_session:
                user = User.get(lambda x: x.ext_id == call.from_user.id)
                if user:
                    bot.edit_message_text(
                        chat_id = call.message.chat.id,
                        message_id = call.message.message_id,
                        text='Статистика за:\n{} - {}'.format(temp, date.strftime('%Y-%m-%d')),
                        #reply_markup=types.ReplyKeyboardRemove()
                    )
                    export_report(user, temp, date.strftime('%Y-%m-%d'))
        else:
            markup = calendar.create_calendar(
                calendar_callback.prefix,
                year=int(year),
                month=int(month),
                day=int(day),
                temp=date.strftime('%Y-%m-%d')
            )
            bot.edit_message_text(
                chat_id = call.message.chat.id,
                message_id = call.message.message_id,
                text='Выберите конечную дату:',
                reply_markup=markup
            )
            bot.answer_callback_query(callback_query_id=call.id)
            return False, None

        #print(f'{calendar_1_callback}: Day: {date.strftime('%d.%m.%Y')}')
    elif action == 'CANCEL':
        bot.send_message(
            chat_id=call.from_user.id,
            text='Вы отменили выгрузку статистики',
            #reply_markup=ReplyKeyboardRemove(),
        )


t = Thread(target=start_scheduler, args=(bot,), daemon=True)
t.start()
bot.infinity_polling()

#bot.polling()

#bot.register_next_step_handler(msg, answer)