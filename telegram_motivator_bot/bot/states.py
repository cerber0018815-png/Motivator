from aiogram.fsm.state import State, StatesGroup

class ReportStates(StatesGroup):
    waiting_evening = State()