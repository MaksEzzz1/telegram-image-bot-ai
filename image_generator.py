# image_generator.py
# -----------------------------------------------------------------------------
# Отвечает за общение с бесплатным Hugging Face Inference API:
#   - text-to-image  (генерация картинки по тексту)
#   - image-to-image (редактирование картинки по инструкции)
#
# Также реализует очередь генераций через asyncio.Semaphore, чтобы не
# отправлять в бесплатный API слишком много параллельных запросов одновременно
# (иначе он начинает отвечать ошибками 503 "model is loading").
# -----------------------------------------------------------------------------

import asyncio
import io
import logging

import aiohttp
from PIL import Image

from config import (
    HF_TOKEN,
    HF_API_URL,
    HF_TEXT2IMG_MODEL,
    HF_IMG2IMG_MODEL,
    HF_REQUEST_TIMEOUT,
    MAX_CONCURRENT_GENERATIONS,
)

logger = logging.getLogger(__name__)

# Семафор ограничивает число ОДНОВРЕМЕННЫХ запросов к Hugging Face.
# Это и есть наша "очередь генерации": если лимит занят, новый запрос
# просто ждёт своей очереди внутри `async with generation_semaphore`.
generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)


class GenerationError(Exception):
    """Наше собственное исключение для читаемых сообщений об ошибках пользователю."""


def _headers() -> dict:
    if not HF_TOKEN:
        raise GenerationError(
            "HF_TOKEN не задан. Получите бесплатный токен на "
            "https://huggingface.co/settings/tokens и добавьте в .env"
        )
    return {"Authorization": f"Bearer {HF_TOKEN}"}


async def _post_to_hf(model: str, payload: bytes, extra_headers: dict | None = None) -> bytes:
    """
    Низкоуровневый запрос к Hugging Face Inference API.
    Возвращает сырые байты изображения (PNG/JPEG) при успехе.
    """
    url = f"{HF_API_URL}{model}"
    headers = _headers()
    if extra_headers:
        headers.update(extra_headers)

    timeout = aiohttp.ClientTimeout(total=HF_REQUEST_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Бесплатные модели на HF иногда "спят" и требуют до 20-60 секунд на
        # прогрев (холодный старт). Делаем несколько попыток с ожиданием.
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with session.post(url, headers=headers, data=payload) as resp:
                    content_type = resp.headers.get("content-type", "")

                    if resp.status == 200 and content_type.startswith("image/"):
                        return await resp.read()

                    # Модель ещё загружается на сервере Hugging Face
                    if resp.status == 503:
                        body = await resp.json(content_type=None)
                        wait_time = float(body.get("estimated_time", 15))
                        logger.info(
                            "Модель %s ещё загружается, ждём %.0f сек (попытка %d/%d)",
                            model, wait_time, attempt, max_retries,
                        )
                        await asyncio.sleep(min(wait_time, 30))
                        continue

                    # Любая другая ошибка API
                    error_text = await resp.text()
                    raise GenerationError(
                        f"Hugging Face вернул ошибку {resp.status}: {error_text[:200]}"
                    )

            except asyncio.TimeoutError:
                raise GenerationError(
                    "Превышено время ожидания ответа от AI-модели. Попробуйте ещё раз."
                )

        raise GenerationError(
            "Модель не смогла загрузиться после нескольких попыток. "
            "Попробуйте повторить запрос через минуту."
        )


async def generate_image_from_text(prompt: str) -> bytes:
    """
    Text-to-image: генерирует изображение по текстовому описанию.
    Возвращает PNG-байты.
    """
    if not prompt or not prompt.strip():
        raise GenerationError("Описание не может быть пустым.")

    payload = {
        "inputs": prompt.strip(),
        "options": {"wait_for_model": True},
    }

    import json
    body = json.dumps(payload).encode("utf-8")

    async with generation_semaphore:
        image_bytes = await _post_to_hf(
            HF_TEXT2IMG_MODEL,
            body,
            extra_headers={"Content-Type": "application/json"},
        )

    return image_bytes


async def edit_image_with_prompt(image_bytes: bytes, prompt: str) -> bytes:
    """
    Image-to-image: изменяет присланное пользователем изображение согласно
    текстовой инструкции (например "сделай зимний пейзаж", "убери фон").
    Возвращает PNG-байты результата.
    """
    if not prompt or not prompt.strip():
        raise GenerationError("Инструкция для редактирования не может быть пустой.")

    # На всякий случай приводим картинку к JPEG разумного размера —
    # это ускоряет загрузку и снижает риск ошибок на стороне API.
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    normalized_bytes = buffer.getvalue()

    # instruct-pix2pix и похожие модели принимают multipart: картинку + текст
    # через заголовок X-Wait-For-Model и параметр "inputs" в form-data.
    import base64
    import json

    payload = {
        "inputs": prompt.strip(),
        "image": base64.b64encode(normalized_bytes).decode("utf-8"),
        "options": {"wait_for_model": True},
    }
    body = json.dumps(payload).encode("utf-8")

    async with generation_semaphore:
        result_bytes = await _post_to_hf(
            HF_IMG2IMG_MODEL,
            body,
            extra_headers={"Content-Type": "application/json"},
        )

    return result_bytes
