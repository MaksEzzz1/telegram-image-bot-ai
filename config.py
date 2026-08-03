# config.py
# -----------------------------------------------------------------------------
# Загружает все настройки бота из переменных окружения (.env файл).
# Ничего не хардкодим: токены, ключи и лимиты живут только в .env
# -----------------------------------------------------------------------------

import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env, который лежит рядом с этим файлом
load_dotenv()

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден! Скопируйте .env.example в .env и вставьте туда "
        "токен, полученный у @BotFather."
    )

# ---------------------------------------------------------------------------
# Hugging Face (бесплатный Inference API)
# ---------------------------------------------------------------------------
# Получить бесплатный токен: https://huggingface.co/settings/tokens
# Права токена: достаточно "Read"
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Модель для генерации изображений по тексту (text-to-image).
# FLUX.1-schnell — быстрая и качественная бесплатная модель.
# Альтернативы: "stabilityai/stable-diffusion-xl-base-1.0",
#               "runwayml/stable-diffusion-v1-5"
HF_TEXT2IMG_MODEL = os.getenv(
    "HF_TEXT2IMG_MODEL", "black-forest-labs/FLUX.1-schnell"
)

# Модель для редактирования изображений по инструкции (image-to-image).
# instruct-pix2pix понимает текстовые инструкции вида "сделай фон синим"
HF_IMG2IMG_MODEL = os.getenv(
    "HF_IMG2IMG_MODEL", "timbrooks/instruct-pix2pix"
)

# Базовый URL Hugging Face Inference API
HF_API_URL = "https://api-inference.huggingface.co/models/"

# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# ---------------------------------------------------------------------------
# Анти-спам / ограничения
# ---------------------------------------------------------------------------
# Сколько секунд пользователь должен ждать между запросами на генерацию
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "20"))

# Сколько одновременных генераций может обрабатывать бот
# (защищает бесплатный API от перегрузки)
MAX_CONCURRENT_GENERATIONS = int(os.getenv("MAX_CONCURRENT_GENERATIONS", "2"))

# Максимальный размер очереди — если больше, новые запросы отклоняются
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "20"))

# Таймаут ожидания ответа от Hugging Face (модель может "просыпаться" долго)
HF_REQUEST_TIMEOUT = int(os.getenv("HF_REQUEST_TIMEOUT", "120"))
