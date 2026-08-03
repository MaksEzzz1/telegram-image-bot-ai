# bot.py
# -----------------------------------------------------------------------------
# Точка входа. Запускает Telegram-бота в режиме long polling.
#
# Запуск:
#   python bot.py
# -----------------------------------------------------------------------------

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN
from database import db
from handlers import all_routers
from keyboards import main_menu_keyboard

# ---------------------------------------------------------------------------
# Логирование — важно для отладки на телефоне/сервере, где нет удобного
# дебаггера. Всё пишется и в консоль, и в файл bot.log.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def create_dispatcher() -> Dispatcher:
    """Создаёт Dispatcher, регистрирует все роутеры и общий catch-all хендлер."""
    dp = Dispatcher(storage=MemoryStorage())

    for router in all_routers:
        dp.include_router(router)

    # ---------------------------------------------------------------------
    # Catch-all хендлер: ловит любые сообщения, которые не подошли ни под
    # один из хендлеров выше (например, пользователь написал случайный текст
    # вне диалога). Должен быть зарегистрирован ПОСЛЕДНИМ.
    # ---------------------------------------------------------------------
    @dp.message(F.text)
    async def fallback_handler(message: Message) -> None:
        await message.answer(
            "Не совсем понял 🤔 Выбери действие в меню снизу или используй /help.",
            reply_markup=main_menu_keyboard(),
        )

    @dp.message()
    async def fallback_any_content(message: Message) -> None:
        await message.answer(
            "Я умею работать с текстом и фото 🙂 Выбери действие в меню снизу.",
            reply_markup=main_menu_keyboard(),
        )

    return dp


async def main() -> None:
    """Инициализирует БД и запускает polling с автоматическим перезапуском."""
    await db.init()
    logger.info("База данных инициализирована.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = await create_dispatcher()

    # Сбрасываем возможные "зависшие" обновления от предыдущего запуска
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот запущен и слушает обновления...")

    # ------------------------------------------------------------------
    # Бесконечный цикл с перезапуском при сбоях — обеспечивает работу 24/7
    # даже если на мгновение пропадёт интернет или произойдёт сетевая
    # ошибка. Между попытками делаем паузу, чтобы не заспамить логи.
    # ------------------------------------------------------------------
    while True:
        try:
            await dp.start_polling(bot)
        except Exception:
            logger.exception("Polling упал с ошибкой, перезапуск через 5 секунд...")
            await asyncio.sleep(5)
        else:
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
