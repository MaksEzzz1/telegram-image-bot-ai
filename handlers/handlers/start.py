# handlers/start.py
# -----------------------------------------------------------------------------
# Команды /start, /help и обработка кнопки "Помощь".
# -----------------------------------------------------------------------------

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import db
from keyboards import main_menu_keyboard, BTN_HELP

router = Router(name="start")


WELCOME_TEXT = (
    "👋 <b>Привет! Я — твой AI-художник в Telegram!</b>\n\n"
    "Я умею:\n"
    "🎨 <b>Рисовать изображения</b> по любому текстовому описанию\n"
    "🖌 <b>Редактировать твои фото</b> по текстовой инструкции\n\n"
    "Всё это — совершенно <b>бесплатно</b>, на основе открытых AI-моделей.\n\n"
    "Выбери действие в меню снизу 👇 или используй команду /help, "
    "чтобы узнать больше."
)

HELP_TEXT = (
    "📖 <b>Как пользоваться ботом</b>\n\n"
    "🎨 <b>Создать изображение</b>\n"
    "Нажми кнопку и просто опиши, что хочешь увидеть, например:\n"
    "<i>«рыжий кот в скафандре на Марсе, цифровая живопись»</i>\n\n"
    "🖌 <b>Изменить фото</b>\n"
    "Нажми кнопку, отправь своё фото, а затем напиши, что изменить, например:\n"
    "<i>«сделай зимний пейзаж» или «преврати в масляную картину»</i>\n\n"
    "⏱ <b>Ограничения</b>\n"
    "Между запросами нужно немного подождать — это защищает бесплатный сервис "
    "от перегрузки и даёт всем пользователям генерировать картинки без сбоев.\n\n"
    "🚫 В любой момент можно нажать «Отмена», чтобы прервать текущий диалог.\n\n"
    "Команды:\n"
    "/start — перезапустить бота и открыть меню\n"
    "/help — показать эту справку"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обрабатывает команду /start: регистрирует пользователя и показывает меню."""
    await state.clear()

    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    """Показывает подробную справку по боту."""
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())
