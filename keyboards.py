# keyboards.py
# -----------------------------------------------------------------------------
# Все клавиатуры бота собраны в одном месте, чтобы было легко поддерживать
# единый стиль интерфейса.
# -----------------------------------------------------------------------------

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Текст кнопок вынесен в константы — используется и в клавиатуре, и в
# обработчиках (чтобы сравнивать message.text с этими же значениями).
BTN_GENERATE = "🎨 Создать изображение"
BTN_EDIT = "🖌 Изменить фото"
BTN_HELP = "❓ Помощь"
BTN_CANCEL = "🚫 Отмена"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота — постоянная клавиатура внизу экрана."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_GENERATE), KeyboardButton(text=BTN_EDIT)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие в меню 👇",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с единственной кнопкой отмены — показывается во время диалога."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def result_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки под результатом генерации: повторить / новое изображение."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔁 Сгенерировать ещё", callback_data="regenerate"),
            ]
        ]
    )
