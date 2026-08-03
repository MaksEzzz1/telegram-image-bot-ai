# handlers/generate.py
# -----------------------------------------------------------------------------
# Диалог генерации изображения по текстовому описанию (text-to-image).
# -----------------------------------------------------------------------------

import logging
import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile, CallbackQuery

from config import COOLDOWN_SECONDS
from database import db
from image_generator import generate_image_from_text, GenerationError
from keyboards import main_menu_keyboard, cancel_keyboard, result_inline_keyboard, BTN_GENERATE, BTN_CANCEL
from states import GenerateStates

logger = logging.getLogger(__name__)
router = Router(name="generate")


async def _check_cooldown(message: Message) -> bool:
    """
    Проверяет анти-спам таймер. Возвращает True, если пользователю можно
    генерировать, иначе отправляет предупреждение и возвращает False.
    """
    last_request = await db.get_last_request_time(message.from_user.id)
    elapsed = time.time() - last_request
    if elapsed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - elapsed)
        await message.answer(
            f"⏳ Подожди ещё {remaining} сек. перед следующим запросом — "
            "это помогает боту работать стабильно для всех пользователей."
        )
        return False
    return True


@router.message(F.text == BTN_GENERATE)
async def start_generate(message: Message, state: FSMContext) -> None:
    """Запускает диалог: просим пользователя описать желаемое изображение."""
    await state.set_state(GenerateStates.waiting_for_prompt)
    await message.answer(
        "✏️ Опиши изображение, которое хочешь получить.\n\n"
        "Например: <i>«футуристический город на закате, неоновые огни, 4k»</i>",
        reply_markup=cancel_keyboard(),
    )


@router.message(GenerateStates.waiting_for_prompt, F.text == BTN_CANCEL)
async def cancel_generate(message: Message, state: FSMContext) -> None:
    """Отмена диалога генерации."""
    await state.clear()
    await message.answer("Отменено. Возвращаю в главное меню.", reply_markup=main_menu_keyboard())


@router.message(GenerateStates.waiting_for_prompt, F.text)
async def process_prompt(message: Message, state: FSMContext) -> None:
    """Получает текстовый промпт от пользователя и запускает генерацию."""
    if not await _check_cooldown(message):
        return

    prompt = message.text.strip()
    await state.update_data(last_prompt=prompt)
    await state.clear()

    await _run_generation(message, prompt)


async def _run_generation(message: Message, prompt: str) -> None:
    """Общая логика генерации + отправки результата пользователю."""
    status_message = await message.answer(
        "🎨 Генерирую изображение... Это может занять от 10 секунд до пары минут "
        "(бесплатная модель иногда «просыпается» дольше обычного).",
        reply_markup=main_menu_keyboard(),
    )

    try:
        image_bytes = await generate_image_from_text(prompt)
        await db.update_last_request(message.from_user.id)

        photo = BufferedInputFile(image_bytes, filename="generated.png")
        await message.answer_photo(
            photo=photo,
            caption=f"✅ Готово!\n\n<b>Промпт:</b> {prompt}",
            reply_markup=result_inline_keyboard(),
        )

    except GenerationError as e:
        logger.warning("Ошибка генерации для user %s: %s", message.from_user.id, e)
        await message.answer(
            f"😔 Не удалось сгенерировать изображение.\n\n<i>{e}</i>\n\n"
            "Попробуй ещё раз через минуту или измени описание."
        )
    except Exception:
        logger.exception("Неожиданная ошибка при генерации")
        await message.answer(
            "⚠️ Произошла непредвиденная ошибка. Мы уже разбираемся! "
            "Попробуй повторить запрос чуть позже."
        )
    finally:
        try:
            await status_message.delete()
        except Exception:
            pass  # сообщение уже могло быть удалено — это не критично


@router.callback_query(F.data == "regenerate")
async def regenerate_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка «Сгенерировать ещё» под результатом — просто открывает новый диалог."""
    await callback.answer()
    await state.set_state(GenerateStates.waiting_for_prompt)
    await callback.message.answer(
        "✏️ Опиши новое изображение:",
        reply_markup=cancel_keyboard(),
    )
