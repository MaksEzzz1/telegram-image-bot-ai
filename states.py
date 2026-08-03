# states.py
# -----------------------------------------------------------------------------
# Состояния диалога (FSM) — определяют, чего бот ждёт от пользователя дальше.
# -----------------------------------------------------------------------------

from aiogram.fsm.state import StatesGroup, State


class GenerateStates(StatesGroup):
    waiting_for_prompt = State()  # ждём текстовое описание для генерации


class EditStates(StatesGroup):
    waiting_for_photo = State()   # ждём фото от пользователя
    waiting_for_prompt = State()  # ждём инструкцию, что изменить на фото
