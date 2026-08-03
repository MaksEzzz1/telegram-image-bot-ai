# handlers/image_edit.py
# -----------------------------------------------------------------------------
# Диалог редактирования пользовательского фото по текстовой инструкции
# (image-to-image).
# -----------------------------------------------------------------------------

import logging
import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile

from config import COOLDOWN_SECONDS
from database import db
from image_generator import edit_image_with_prompt, GenerationError
from keyboards import main_menu_keyboard, cancel_keyboard, BTN_EDIT, BTN_CANCEL
from states import EditStates

logger = logging.getLogger(__name__)
router = Router(name="image_edit")


async def _check_cooldown(message: Message) -> bool:
    """Та же логика анти-спама, что и в handlers/generate.py."""
    last_request = await db.get_last_request_time(message.from_user.id)
    elapsed = time.time() - last_request
    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed)
        await message.answer(
            f"⏳ Подожди ещё {remaining} сек. перед следующим запросом."
        )
        return False
    return True


@router.message(F.text == BTN_EDIT)
async def start_edit(message: Message, state: FSMContext) -> None:
    """Запускает диалог: просим пользователя прислать фото."""
    await state.set_state(EditStates.waiting_for_photo)
    await message.answer(
        "📸 Отправь мне фото, которое хочешь изменить.",
        reply_markup=cancel_keyboard(),
    )


@router.message(EditStates.waiting_for_photo, F.text == BTN_CANCEL)
@router.message(EditStates.waiting_for_prompt, F.text == BTN_CANCEL)
async def cancel_edit(message: Message, state: FSMContext) -> None:
    """Отмена диалога редактирования на любом этапе."""
    await state.clear()
    await message.answer("Отменено. Возвращаю в главное меню.", reply_markup=main_menu_keyboard())


@router.message(EditStates.waiting_for_photo, F.photo)
async def receive_photo(message: Message, state: FSMContext) -> None:
    """Получает фото, сохраняет его file_id и просит текстовую инструкцию."""
    # Берём самое качественное доступное разрешение (последнее в списке)
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=file_id)
    await state.set_state(EditStates.waiting_for_prompt)

    await message.answer(
        "✏️ Что изменить на этом фото?\n\n"
        "Например: <i>«сделай в стиле аниме» или «добавь снег»</i>",
        reply_markup=cancel_keyboard(),
    )


@router.message(EditStates.waiting_for_photo)
async def wrong_content_type(message: Message) -> None:
    """Если пользователь прислал не фото — вежливо просим прислать именно фото."""
    await message.answer("Пожалуйста, отправь именно фотографию 📷")


@router.message(EditStates.waiting_for_prompt, F.text)
async def process_edit_prompt(message: Message, state: FSMContext) -> None:
    """Получает инструкцию редактирования и запускает обработку изображения."""
    if not await _check_cooldown(message):
        return

    data = await state.get_data()
    file_id = data.get("photo_file_id")
    prompt = message.text.strip()
    await state.clear()

    if not file_id:
        await message.answer(
            "Что-то пошло не так — фото не найдено. Начни заново.",
            reply_markup=main_menu_keyboard(),
        )
        return

    status_message = await message.answer(
        "🖌 Обрабатываю изображение... Это может занять до пары минут.",
        reply_markup=main_menu_keyboard(),
    )

    try:
        # Скачиваем оригинальное фото с серверов Telegram
        bot = message.bot
        file = await bot.get_file(file_id)
        file_bytes_io = await bot.download_file(file.file_path)
        original_bytes = file_bytes_io.read()

        result_bytes = await edit_image_with_prompt(original_bytes, prompt)
        await db.update_last_request(message.from_user.id)

        photo = BufferedInputFile(result_bytes, filename="edited.png")
        await message.answer_photo(
            photo=photo,
            caption=f"✅ Готово!\n\n<b>Инструкция:</b> {prompt}",
        )

    except GenerationError as e:
        logger.warning("Ошибка редактирования для user %s: %s", message.from_user.id, e)
        await message.answer(
            f"😔 Не удалось изменить изображение.\n\n<i>{e}</i>\n\n"
            "Попробуй ещё раз или используй другую инструкцию."
        )
    except Exception:
        logger.exception("Неожиданная ошибка при редактировании изображения")
        await message.answer(
            "⚠️ Произошла непредвиденная ошибка при обработке фото. "
            "Попробуй повторить запрос чуть позже."
        )
    finally:
        try:
            await status_message.delete()
        except Exception:
            pass
