import asyncio
import re
from datetime import datetime, time, timedelta
from typing import Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, TelegramObject
from bestconfig import Config
from gspread import Worksheet

from gsheet import GSheetConnector, sheet2pandas


class ChatFilter(BaseFilter):
    def __init__(self, chat_id: str | int):
        self.chat_id = chat_id

    async def __call__(self, message: Message) -> bool:
        return message.chat.id == self.chat_id


class GSheetMiddleware(BaseMiddleware):
    def __init__(self, fabric: GSheetConnector, table_id: str):
        self.fabric = fabric
        self.table_id = table_id

    async def __call__(self, handler: Callable, event: TelegramObject, data: dict):
        data["user_table"] = self.fabric.get_sheet(self.table_id).sheet1
        await handler(event, data)


config = Config()

bot = Bot(config.token)
dp = Dispatcher()
connector = GSheetConnector()
dp.message.middleware(GSheetMiddleware(connector, table_id=config.table_id))

CHAT_FILTER = ChatFilter(config.chat_id)


@dp.message(Command("me"), CHAT_FILTER)
async def about_me(message: Message, user_table: Worksheet):
    # Если все нормально, получаем таблицу с пользователями
    table, first_line = sheet2pandas(user_table)

    # Получаем пользователя
    user_index = table[
        table["Telegram"].str.strip().str.lower()
        == f"@{message.from_user.username.lower()}"
    ].index[0]

    column_index = table.columns.tolist().index(datetime.now().strftime("%d.%m.%Y")) + 1
    result = table.iloc[user_index, column_index - 1]

    # Если проспал
    if '1' in result:
        await message.answer(f"{message.from_user.first_name}, ты сегодня проспал 😢")
    # Если встал вовремя
    elif '0' in result:
        await message.answer(f"{message.from_user.first_name}, ты сегодня встал вовремя ☀️")
    # Если не прислал кружок
    else:
        await message.answer(f"{message.from_user.first_name}, ты сегодня еще не присылал кружочек 👀")

@dp.message(Command("help"), CHAT_FILTER)
async def help(message: Message):
    await message.answer("Привет, я бот который записывает твои подъемы в таблицу")


@dp.message(CHAT_FILTER)
async def circle_heandler(message: Message, user_table: Worksheet):
    # Обрабатываем пришедший кружочек
    # Проверяем что он не выходит за рамки утра
    message_time = (message.date + timedelta(hours=3)).time()
    if not (time(4) < message_time < time(10)):
        return

    # Если все нормально, получаем таблицу с пользователями
    table, first_line = sheet2pandas(user_table)

    # Получаем пользователя
    user_index = table[
        table["Telegram"].str.strip().str.lower()
        == f"@{message.from_user.username.lower()}"
    ].index[0]
    user = table.loc[user_index].to_dict()
    # Если пользователя нет в таблице, ничего не делаем
    if not user:
        return

    # Определяем время просыпания пользователя
    # Берется самое позднее его время
    wakeup_time = user["Время подъема (мск)"]
    wakeup_time = re.findall(r"\d+(?:[:\.]\d+)?", wakeup_time.replace(" ", ""))
    wakeup_time = time(*map(int, (re.findall(r"\d+", wakeup_time[-1]))))

    # Определяем координаты ячейки для записи
    row_index = user_index + first_line + 2
    column_index = table.columns.tolist().index(datetime.now().strftime("%d.%m.%Y")) + 1
    # Если нет колонки с текущей датой, значит челендж не идет
    if column_index == 0:
        return

    # Если пользователь проснулся вовремя, ставим в таблице значение 0
    # А если проспал - -1000
    if message_time > wakeup_time:
        await message.answer(
            f"Ты проспал время своего подъема ({wakeup_time.strftime('%H:%M').lstrip('0')}) 😢"
        )
        user_table.update_cell(row_index, column_index, -1000)
    else:
        await message.answer("С добрым утром ☀️")
        user_table.update_cell(row_index, column_index, 0)


asyncio.run(dp.start_polling(bot))
