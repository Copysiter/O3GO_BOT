import calendar
import typing
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery


@dataclass
class Language:
    days: tuple
    months: tuple


ENGLISH_LANGUAGE = Language(
    days=("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"),
    months=(
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
)

RUSSIAN_LANGUAGE = Language(
    days=("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"),
    months=(
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ),
)


class Calendar:
    """
    Calendar data factory
    """

    __lang: Language

    def __init__(self, language: Language = ENGLISH_LANGUAGE):
        self.__lang = language

    def create_calendar(
        self,
        name: str = "calendar",
        year: int = None,
        month: int = None,
        day: int = None,
        temp: str = ""
    ) -> InlineKeyboardMarkup:
        """
        Create a built in inline keyboard with calendar
        :param name:
        :param year: Year to use in the calendar if you are not using the current year.
        :param month: Month to use in the calendar if you are not using the current month.
        :return: Returns an InlineKeyboardMarkup object with a calendar.
        """

        now_day = datetime.now()

        if year is None:
            year = now_day.year
        if month is None:
            month = now_day.month
        if day is None:
            day = now_day.day

        temp_date = temp if len(temp) > 0 else datetime.now().strftime("%Y-%m-%d")

        calendar_callback = CallbackData(name, "action", "year", "month", "day", "temp")
        data_ignore = calendar_callback.new("IGNORE", year, month, day, temp)
        data_months = calendar_callback.new("MONTHS", year, month, day, temp)

        keyboard = InlineKeyboardMarkup(row_width=7)

        keyboard.add(
            InlineKeyboardButton(
                self.__lang.months[month - 1] + " " + str(year),
                callback_data=data_months,
            )
        )

        keyboard.add(
            *[
                InlineKeyboardButton(day, callback_data=data_ignore)
                for day in self.__lang.days
            ]
        )

        for week in calendar.monthcalendar(year, month):
            row = list()
            for i in range(len(week)):
                if week[i] == 0:
                    row.append(InlineKeyboardButton(" ", callback_data=data_ignore))
                elif (
                    date(year, month, week[i]).strftime('%Y-%m-%d')
                    == temp_date
                ):
                    row.append(
                        InlineKeyboardButton(
                            f"📍",
                            callback_data=calendar_callback.new(
                                "DAY", year, month, week[i], temp
                            ),
                        )
                    )
                else:
                    row.append(
                        InlineKeyboardButton(
                            str(week[i]),
                            callback_data=calendar_callback.new(
                                "DAY", year, month, week[i], temp
                            ),
                        )
                    )
            keyboard.add(*row)

        keyboard.add(
            InlineKeyboardButton(
                "<",
                callback_data=calendar_callback.new("PREVIOUS-MONTH", year, month, day, temp),
            ),
            InlineKeyboardButton(
                "Отмена",
                callback_data=calendar_callback.new("CANCEL", year, month, day, temp),
            ),
            InlineKeyboardButton(
                ">", callback_data=calendar_callback.new("NEXT-MONTH", year, month, day, temp)
            ),
        )

        return keyboard

    def create_months_calendar(
        self, name: str = "calendar", year: int = None, temp: str = ""
    ) -> InlineKeyboardMarkup:
        """
        Creates a calendar with month selection
        :param name:
        :param year:
        :return:
        """

        if year is None:
            year = datetime.now().year

        calendar_callback = CallbackData(name, "action", "year", "month", "day", "temp")

        keyboard = InlineKeyboardMarkup()

        for i, month in enumerate(
            zip(self.__lang.months[0::2], self.__lang.months[1::2])
        ):
            keyboard.add(
                InlineKeyboardButton(
                    month[0],
                    callback_data=calendar_callback.new("MONTH", year, 2 * i + 1, 0, temp=temp),
                ),
                InlineKeyboardButton(
                    month[1],
                    callback_data=calendar_callback.new(
                        "MONTH", year, (i + 1) * 2, 0, temp=temp
                    ),
                ),
            )

        return keyboard

    def calendar_query_handler(
        self,
        bot: TeleBot,
        call: CallbackQuery,
        name: str,
        action: str,
        year: int,
        month: int,
        day: int,
        temp: str = ""
    ) -> None or datetime:
        """
        The method creates a new calendar if the forward or backward button is pressed
        This method should be called inside CallbackQueryHandler.
        :param bot: The object of the bot CallbackQueryHandler
        :param call: CallbackQueryHandler data
        :param day:
        :param month:
        :param year:
        :param action:
        :param name:
        :return: Returns a tuple
        """

        current = datetime(int(year), int(month), 1)
        if action == "IGNORE":
            bot.answer_callback_query(callback_query_id=call.id)
            return False, None
        elif action == "DAY":
            '''
            bot.delete_message(
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
            '''
            return datetime(int(year), int(month), int(day))
        elif action == "PREVIOUS-MONTH":
            preview_month = current - timedelta(days=1)
            bot.edit_message_text(
                text=call.message.text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.create_calendar(
                    name=name,
                    year=int(preview_month.year),
                    month=int(preview_month.month),
                    day=int(day),
                    temp=temp
                ),
            )
            return None
        elif action == "NEXT-MONTH":
            next_month = current + timedelta(days=31)
            bot.edit_message_text(
                text=call.message.text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.create_calendar(
                    name=name,
                    year=int(next_month.year),
                    month=int(next_month.month),
                    day=int(day),
                    temp=temp
                ),
            )
            return None
        elif action == "MONTHS":
            bot.edit_message_text(
                text=call.message.text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.create_months_calendar(name=name, year=current.year, temp=temp),
            )
            return None
        elif action == "MONTH":
            bot.edit_message_text(
                text=call.message.text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.create_calendar(
                    name=name,
                    year=int(year),
                    month=int(month),
                    day=int(day),
                    temp=temp
                ),
            )
            return None
        elif action == "CANCEL":
            bot.delete_message(
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
            return "CANCEL", None
        else:
            bot.answer_callback_query(callback_query_id=call.id, text="ERROR!")
            bot.delete_message(
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
            return None


class CallbackData:
    """
    Callback data factory
    """

    def __init__(self, prefix, *parts, sep=":"):
        if not isinstance(prefix, str):
            raise TypeError(
                f"Prefix must be instance of str not {type(prefix).__name__}"
            )
        if not prefix:
            raise ValueError("Prefix can't be empty")
        if sep in prefix:
            raise ValueError(f"Separator {sep!r} can't be used in prefix")
        if not parts:
            raise TypeError("Parts were not passed!")

        self.prefix = prefix
        self.sep = sep

        self._part_names = parts

    def new(self, *args, **kwargs) -> str:
        """
        Generate callback data
        :param args:
        :param kwargs:
        :return:
        """

        args = list(args)

        data = [self.prefix]
        for part in self._part_names:
            value = kwargs.pop(part, None)
            #if part != 'temp':
            if value is None:
                if args:
                    value = args.pop(0)
                else:
                    raise ValueError(f"Value for {part!r} was not passed!")

            if value is not None and not isinstance(value, str):
                value = str(value)

            if not value and part != "temp":
                raise ValueError(f"Value for part {part!r} can't be empty!'")
            if self.sep in value:
                raise ValueError(
                    f"Symbol {self.sep!r} is defined as the separator and can't be used in parts' values"
                )

            data.append(value)

        if args or kwargs:
            raise TypeError("Too many arguments were passed!")

        callback_data = self.sep.join(data)
        if len(callback_data) > 64:
            raise ValueError("Resulted callback data is too long!")

        return callback_data

    def parse(self, callback_data: str) -> typing.Dict[str, str]:
        """
        Parse data from the callback data
        :param callback_data:
        :return:
        """

        prefix, *parts = callback_data.split(self.sep)

        if prefix != self.prefix:
            raise ValueError("Passed callback data can't be parsed with that prefix.")
        elif len(parts) != len(self._part_names):
            raise ValueError("Invalid parts count!")

        result = {"@": prefix}
        result.update(zip(self._part_names, parts))

        return result

    def filter(self, **config):
        """
        Generate filter
        :param config:
        :return:
        """

        print(config, self._part_names)
        for key in config.keys():
            if key not in self._part_names:
                return False

        return True