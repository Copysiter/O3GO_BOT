import requests
import time
import prettytable as pt

from datetime import datetime, timedelta

from telebot import TeleBot

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger

from config import *

from pony.orm import *
from db import *

def start_scheduler(bot: TeleBot):
    def send_user_report():
        date = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d 00:00:00')
        day = (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y')
        response = requests.get(REG_API_ADDR, params={'date': date})
        data = response.json()
        report = f'<b>Статистика по пользователям:</b>\n\n';
        for user, data in data.items():
            table = pt.PrettyTable(['Service', 'Success', 'Total'])
            table.align['Service'] = 'l'
            table.align['Success'] = 'r'
            table.align['Total'] = 'r'
            report += f'<b>{user}</b>\n'
            for service, data in data.items():
                if len(service) > 10:
                    service = service[:11] + '...'
                else:
                    service = service + ' ' * (14 - len(service))
                table.add_row([service, data['success'], data['total']])
            report += f'<pre>{table}</pre>\n\n'
        with db_session:
            for superuser in User.select(lambda x: x.is_active):
                bot.send_message(
                        superuser.ext_id,
                        report, parse_mode='HTML'
                    )

    scheduler = BackgroundScheduler({'apscheduler.timezone': 'UTC'})

    trigger = OrTrigger([
        CronTrigger(month='*', day='*',  hour=(h-3), minute=0) for h in [12, 17, 21]
    ])

    scheduler.add_job(send_user_report, trigger)
    # scheduler.add_job(send_user_report, trigger='cron', month='*', day='*',  hour='*', minute='*/1')

    scheduler.start()
