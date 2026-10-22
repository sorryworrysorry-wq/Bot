import re
import json
import os
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ============== ЛОГИРОВАНИЕ ==============

LOG_FILE = "bot.log"

log_format = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S"
)

log = logging.getLogger("bot")
log.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
log.addHandler(console_handler)

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(log_format)
log.addHandler(file_handler)


def log_user(message: Message, action: str):
    uname = message.from_user.username or "без_username"
    uid = message.from_user.id
    log.info(f"👤 @{uname} (ID: {uid}) → {action}")


# ============== КОНФИГ ==============

API_TOKEN = "8695825408:AAHcyHDbAKUZevyQwmI8PYwhQVm_-PvpXjI"
YOUR_CHAT_ID = 1625987729

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

VPN_FILE = "vpn_keys.json"
OLYMP_FILE = "olympiads.json"
DZ_FILE = "dz.json"
KONSP_FILE = "konspekty.json"
SUBJECTS_FILE = "subjects.json"
BLACKLIST_FILE = "blacklist.json"
OTV_FILE = "otv.json"
STEPIK_FILE = "stepik.json"
YAKIDS_FILE = "ya.kids.json"
MODS_FILE = "mods.json"


class Form(StatesGroup):
    waiting_stepik = State()
    waiting_yandex = State()
    waiting_support = State()
    waiting_equation = State()
    waiting_russian = State()
    waiting_olymp_name = State()
    waiting_olymp_content = State()
    waiting_dz_subject = State()
    waiting_dz_title = State()
    waiting_dz_content = State()
    waiting_konsp_subject = State()
    waiting_konsp_title = State()
    waiting_konsp_content = State()
    waiting_new_subject = State()
    waiting_otv_subject = State()
    waiting_otv_topic = State()
    waiting_otv_content = State()


# ============== МОДЕРАТОРЫ ==============

ALL_MOD_COMMANDS = [
    "addkonsp",
    "adddz",
    "addolymp",
    "addotv",
    "addvpn",
    "subjects",
    "blacklist",
    "reply",
    "stepiklist",
    "yakidslist",
    "logs",
    "reload",
    "all",
]


def load_mods():
    if not os.path.exists(MODS_FILE):
        return {}
    try:
        with open(MODS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_mods(data):
    with open(MODS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_mod(user_id: int, command: str, username: str = ""):
    data = load_mods()
    key = str(user_id)

    if key not in data:
        data[key] = {
            "username": f"@{username}" if username else "no_username",
            "commands": [],
            "date": datetime.now().strftime("%d.%m.%Y %H:%M")
        }

    if command not in data[key]["commands"]:
        data[key]["commands"].append(command)
        save_mods(data)
        log.info(f"👑 Модератор {user_id} получил доступ к: {command}")
        return True
    return False


def del_mod(user_id: int, command: str):
    data = load_mods()
    key = str(user_id)

    if key not in data:
        return False

    if command == "all" or command not in data[key]["commands"]:
        del data[key]
        save_mods(data)
        log.info(f"👑 Модератор {user_id} удален полностью")
        return True

    data[key]["commands"].remove(command)
    if not data[key]["commands"]:
        del data[key]

    save_mods(data)
    log.info(f"👑 У {user_id} отозван доступ к: {command}")
    return True


def is_mod(user_id: int, command: str = None):
    if user_id == YOUR_CHAT_ID:
        return True

    data = load_mods()
    key = str(user_id)

    if key not in data:
        return False

    commands = data[key]["commands"]
    if "all" in commands:
        return True

    if command is None:
        return True

    return command in commands


def get_mod_commands(user_id: int):
    if user_id == YOUR_CHAT_ID:
        return ["all"]
    data = load_mods()
    key = str(user_id)
    if key not in data:
        return []
    return data[key]["commands"]


# ============== STEPIK ==============

def load_stepik():
    if not os.path.exists(STEPIK_FILE):
        return {}
    try:
        with open(STEPIK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.error(f"❌ Ошибка чтения stepik.json: {e}")
        return {}


def save_stepik_file(data):
    with open(STEPIK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_stepik_data(user_id: int, username: str, email: str, password: str):
    data = load_stepik()
    uname = username or "no_username"
    key = f"@{uname}:{user_id}"

    data[key] = {
        "user_id": user_id,
        "username": f"@{uname}",
        "email": email,
        "password": password,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }

    save_stepik_file(data)
    log.info(f"💾 Stepik сохранён: {key}")
    return True


def get_all_stepik():
    return load_stepik()


# ============== ЯНДЕКС УЧЕБНИК ==============

def load_yakids():
    if not os.path.exists(YAKIDS_FILE):
        return {}
    try:
        with open(YAKIDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.error(f"❌ Ошибка чтения ya.kids.json: {e}")
        return {}


def save_yakids_file(data):
    with open(YAKIDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_yakids_data(user_id: int, username: str, login: str, password: str):
    data = load_yakids()
    uname = username or "no_username"
    key = f"@{uname}:{user_id}"

    data[key] = {
        "user_id": user_id,
        "username": f"@{uname}",
        "login": login,
        "password": password,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }

    save_yakids_file(data)
    log.info(f"💾 Я.Учебник сохранён: {key}")
    return True


def get_all_yakids():
    return load_yakids()


# ============== ЧЁРНЫЙ СПИСОК ==============

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return {}
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_blacklist(data):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_to_blacklist(user_id: int, reason: str = ""):
    data = load_blacklist()
    key = str(user_id)
    if key in data:
        return False
    data[key] = {
        "reason": reason or "без причины",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_blacklist(data)
    log.info(f"🚫 Заблокирован: {user_id} ({reason})")
    return True


def remove_from_blacklist(user_id: int):
    data = load_blacklist()
    key = str(user_id)
    if key in data:
        del data[key]
        save_blacklist(data)
        log.info(f"✅ Разблокирован: {user_id}")
        return True
    return False


def is_blacklisted(user_id: int):
    return str(user_id) in load_blacklist()


# ============== ОТВЕТЫ НА ТЕМЫ ==============

def load_otv():
    if not os.path.exists(OTV_FILE):
        return {}
    try:
        with open(OTV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_otv(data):
    with open(OTV_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_otv(subject, topic, content, author):
    data = load_otv()
    key = f"{subject.lower().strip()}|{topic.lower().strip()}"
    if key in data:
        return False
    data[key] = {
        "subject": subject, "topic": topic, "content": content,
        "author": author, "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_otv(data)
    return True


def get_otv(subject, topic):
    data = load_otv()
    key = f"{subject.lower().strip()}|{topic.lower().strip()}"
    return data.get(key)


def get_all_otv():
    return load_otv()


def delete_otv(subject, topic):
    data = load_otv()
    key = f"{subject.lower().strip()}|{topic.lower().strip()}"
    if key in data:
        del data[key]
        save_otv(data)
        return True
    return False


def get_otv_subjects():
    data = load_otv()
    subjects = {}
    for key, item in data.items():
        subj = item["subject"]
        if subj not in subjects:
            subjects[subj] = []
        subjects[subj].append(item["topic"])
    return subjects


# ============== ПРЕДМЕТЫ ==============

DEFAULT_SUBJECTS = [
    "Алгебра", "Геометрия", "Русский язык", "Литература",
    "История", "Обществознание", "Физика", "Химия",
    "Биология", "География", "Английский язык", "Информатика"
]


def load_subjects():
    if not os.path.exists(SUBJECTS_FILE):
        save_subjects(DEFAULT_SUBJECTS)
        return DEFAULT_SUBJECTS.copy()
    try:
        with open(SUBJECTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else DEFAULT_SUBJECTS.copy()
    except Exception:
        return DEFAULT_SUBJECTS.copy()


def save_subjects(data):
    with open(SUBJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_subject(name):
    data = load_subjects()
    if name in data:
        return False
    data.append(name)
    save_subjects(data)
    return True


def get_subject_by_index(idx: int):
    subjects = load_subjects()
    if 0 <= idx < len(subjects):
        return subjects[idx]
    return None


# ============== VPN ==============

def load_vpn_keys():
    if not os.path.exists(VPN_FILE):
        return {}
    try:
        with open(VPN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_vpn_keys(data):
    with open(VPN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_vpn_key(key, name=""):
    data = load_vpn_keys()
    for _, existing in data.items():
        if existing == key:
            return False
    if not name:
        name = f"VPN #{len(data) + 1}"
    data[name] = key
    save_vpn_keys(data)
    return True


def get_all_vpn_keys():
    return load_vpn_keys()


def delete_vpn_key(name):
    data = load_vpn_keys()
    if name in data:
        del data[name]
        save_vpn_keys(data)
        return True
    return False


# ============== ОЛИМПИАДЫ ==============

def load_olympiads():
    if not os.path.exists(OLYMP_FILE):
        return {}
    try:
        with open(OLYMP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_olympiads(data):
    with open(OLYMP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_olympiad(name, content, author):
    data = load_olympiads()
    key = name.lower().strip()
    if key in data:
        return False
    data[key] = {
        "name": name, "content": content, "author": author,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_olympiads(data)
    return True


def get_all_olympiads():
    return load_olympiads()


def delete_olympiad(name):
    data = load_olympiads()
    key = name.lower().strip()
    if key in data:
        del data[key]
        save_olympiads(data)
        return True
    return False


# ============== ДЗ ==============

def load_dz():
    if not os.path.exists(DZ_FILE):
        return {}
    try:
        with open(DZ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_dz(data):
    with open(DZ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_dz(subject, title, content, author):
    data = load_dz()
    key = f"{subject.lower().strip()}|{title.lower().strip()}"
    if key in data:
        return False
    data[key] = {
        "subject": subject, "title": title, "content": content,
        "author": author, "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_dz(data)
    return True


def get_dz_by_key(subject, title):
    data = load_dz()
    key = f"{subject.lower().strip()}|{title.lower().strip()}"
    return data.get(key)


def get_all_dz():
    return load_dz()


def delete_dz(subject, title):
    data = load_dz()
    key = f"{subject.lower().strip()}|{title.lower().strip()}"
    if key in data:
        del data[key]
        save_dz(data)
        return True
    return False


def get_dz_subjects():
    data = load_dz()
    subjects = {}
    for key, item in data.items():
        subj = item["subject"]
        if subj not in subjects:
            subjects[subj] = []
        subjects[subj].append(item["title"])
    return subjects


# ============== КОНСПЕКТЫ ==============

def load_konspekty():
    if not os.path.exists(KONSP_FILE):
        return {}
    try:
        with open(KONSP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_konspekty(data):
    with open(KONSP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_konspekt(subject, title, content, author):
    data = load_konspekty()
    key = f"{subject.lower().strip()}|{title.lower().strip()}"
    if key in data:
        return False
    data[key] = {
        "subject": subject, "title": title, "content": content,
        "author": author, "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_konspekty(data)
    return True


def get_konspekt_by_key(subject, title):
    data = load_konspekty()
    key = f"{subject.lower().strip()}|{title.lower().strip()}"
    return data.get(key)


def get_all_konspekty():
    return load_konspekty()


def delete_konspekt(subject, title):
    data = load_konspekty()
    key = f"{subject.lower().strip()}|{title.lower().strip()}"
    if key in data:
        del data[key]
        save_konspekty(data)
        return True
    return False


def get_konsp_subjects():
    data = load_konspekty()
    subjects = {}
    for key, item in data.items():
        subj = item["subject"]
        if subj not in subjects:
            subjects[subj] = []
        subjects[subj].append(item["title"])
    return subjects


# ============== УРАВНЕНИЯ ==============

def parse_side(side):
    side = side.replace(" ", "")
    if side and side[0] not in "+-":
        side = "+" + side
    terms = re.findall(r'[+-][^+-]+', side)
    a = 0
    b = 0
    for term in terms:
        sign = -1 if term[0] == '-' else 1
        body = term[1:]
        if not body:
            continue
        if re.search(r'[a-zA-Zа-яА-Я]', body):
            nums = re.sub(r'[a-zA-Zа-яА-Я]', '', body)
            if nums == "" or nums == "+":
                a += sign * 1
            elif nums == "-":
                a += sign * (-1)
            else:
                a += sign * (float(nums) if '.' in nums else int(nums))
        else:
            b += sign * (float(body) if '.' in body else int(body))
    return a, b


def fmt(n):
    if isinstance(n, float) and n.is_integer():
        return str(int(n))
    return str(n)


def solve_equation(eq):
    eq = eq.replace(" ", "")
    if "=" not in eq:
        return "❌ Нет знака '='!"
    left, right = eq.split("=", 1)
    try:
        a1, b1 = parse_side(left)
        a2, b2 = parse_side(right)
    except Exception as e:
        return f"❌ Ошибка разбора: {e}"

    A = a1 - a2
    B = b1 - b2

    lines = [f"📝 Уравнение: {left} = {right}", ""]
    lines.append("Шаг 1. Переносим всё в левую часть:")
    left_parts = []
    if a1 != 0:
        left_parts.append(f"{fmt(a1)}x")
    if b1 != 0:
        left_parts.append(fmt(b1))
    right_parts = []
    if a2 != 0:
        right_parts.append(f"{'-' if a2 > 0 else '+'}{fmt(abs(a2))}x")
    if b2 != 0:
        right_parts.append(f"{'-' if b2 > 0 else '+'}{fmt(abs(b2))}")
    lstr = " ".join(left_parts) if left_parts else "0"
    rstr = " ".join(right_parts) if right_parts else ""
    lines.append(f"   {lstr} {rstr} = 0")
    lines.append("")
    lines.append("Шаг 2. Приводим подобные:")
    lines.append(f"   {fmt(A)}x + {fmt(B)} = 0")
    lines.append("")
    lines.append("Шаг 3. Переносим число:")
    lines.append(f"   {fmt(A)}x = {fmt(-B)}")
    lines.append("")
    if A == 0:
        if B == 0:
            lines.append("✅ x — любое число")
        else:
            lines.append("❌ Решений нет")
        return "\n".join(lines)
    x = -B / A
    lines.append("Шаг 4. Делим на коэффициент:")
    lines.append(f"   x = {fmt(-B)} / {fmt(A)}")
    lines.append("")
    lines.append(f"✅ Ответ: x = {fmt(x)}")
    return "\n".join(lines)


def solve_russian(task):
    task_lower = task.lower().strip()
    result = ["📚 Задание по русскому языку", f"📝 Текст: {task}", ""]
    if "встав" in task_lower or "_" in task or "пропущ" in task_lower:
        result.append("🔤 Вставить пропущенные буквы:")
        result.append("1. Прочитай слово")
        result.append("2. Определи часть слова")
        result.append("3. Вспомни правило")
        result.append("4. Вставь букву")
        return "\n".join(result)
    if "морфолог" in task_lower:
        result.append("🔍 Морфологический разбор:")
        result.append("1. Часть речи")
        result.append("2. Начальная форма")
        result.append("3. Постоянные признаки")
        result.append("4. Непостоянные")
        result.append("5. Синтаксическая роль")
        return "\n".join(result)
    if "синтакс" in task_lower:
        result.append("📖 Синтаксический разбор:")
        result.append("1. Грамматическая основа")
        result.append("2. Тип предложения")
        result.append("3. Второстепенные члены")
        result.append("4. Схема")
        return "\n".join(result)
    result.append("🤔 Уточни задание")
    return "\n".join(result)


# ============== МЕНЮ ==============

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="💻 Информатика")],
            [types.KeyboardButton(text="Решить уравнение")],
            [types.KeyboardButton(text="Русский язык")],
            [types.KeyboardButton(text="📝 Олимпиады")],
            [types.KeyboardButton(text="📚 ЦДЗ")],
            [types.KeyboardButton(text="📖 Конспекты")],
            [types.KeyboardButton(text="✏️ Ответы")],
            [types.KeyboardButton(text="🔐 VPN")],
            [types.KeyboardButton(text="Поддержка")]
        ],
        resize_keyboard=True
    )


def informatics_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Stepik")],
            [types.KeyboardButton(text="Яндекс учебник")],
            [types.KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


def subjects_keyboard(prefix: str, with_add: bool = False):
    subjects = load_subjects()
    buttons = []
    row = []
    for i, subj in enumerate(subjects):
        row.append(InlineKeyboardButton(text=subj, callback_data=f"{prefix}:{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if with_add:
        buttons.append([InlineKeyboardButton(text="➕ Добавить предмет", callback_data=f"{prefix}:__add__")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data=f"{prefix}:__cancel__")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subjects_view_keyboard(items_dict: dict, prefix: str):
    buttons = []
    row = []
    for i, subj in enumerate(items_dict.keys()):
        count = len(items_dict[subj])
        row.append(InlineKeyboardButton(
            text=f"{subj} ({count})",
            callback_data=f"{prefix}:{i}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{prefix}:__back__")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def titles_keyboard(subject: str, titles: list, prefix: str):
    buttons = []
    for i, t in enumerate(titles):
        buttons.append([InlineKeyboardButton(
            text=t,
            callback_data=f"{prefix}:{i}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{prefix}:__back__")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============== ЗАБЛОКИРОВАННЫЕ ==============

@dp.message(StateFilter(None), lambda m: is_blacklisted(m.from_user.id))
async def blocked_user(message: Message):
    log.info(f"🚫 Заблокированный @{message.from_user.username} пытался писать")
    await message.answer("🚫 Вы заблокированы владельцем бота.")


# ============== ХЕНДЛЕРЫ ==============

@dp.message(Command("start"))
async def start(message: Message):
    if is_blacklisted(message.from_user.id):
        await message.answer("🚫 Вы заблокированы.")
        return

    log_user(message, "команда /start")
    await message.answer(
        "👋 Привет! Выбери действие:\n"
        "• 💻 Информатика\n"
        "• Решить уравнение\n"
        "• Русский язык\n"
        "• 📝 Олимпиады\n"
        "• 📚 ЦДЗ\n"
        "• 📖 Конспекты\n"
        "• ✏️ Ответы\n"
        "• 🔐 VPN\n"
        "• Поддержка",
        reply_markup=main_menu()
    )


@dp.message(lambda m: m.text == "💻 Информатика")
async def informatics_btn(message: Message, state: FSMContext):
    log_user(message, "открыл '💻 Информатика'")
    await state.clear()
    await message.answer(
        "💻 Категория: Информатика\n\n"
        "• Stepik — почта:пароль\n"
        "• Яндекс учебник — логин:пароль",
        reply_markup=informatics_menu()
    )


@dp.message(lambda m: m.text == "⬅️ Назад")
async def back_btn(message: Message, state: FSMContext):
    log_user(message, "вернулся в главное меню")
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=main_menu())


# ============== STEPIK ==============

@dp.message(lambda m: m.text == "Stepik")
async def stepik_btn(message: Message, state: FSMContext):
    log_user(message, "нажал 'Stepik'")
    await state.set_state(Form.waiting_stepik)
    await message.answer("📧 Введите почта:пароль от Stepik")


@dp.message(Form.waiting_stepik)
async def save_stepik(message: Message, state: FSMContext):
    try:
        if message.text == "⬅️ Назад":
            await state.clear()
            await message.answer("🏠 Главное меню", reply_markup=main_menu())
            return

        creds = message.text.strip()
        if ":" not in creds:
            await message.answer("❌ Формат: почта:пароль")
            return

        email, password = creds.split(":", 1)
        email = email.strip()
        password = password.strip()

        user_id = message.from_user.id
        username = message.from_user.username

        add_stepik_data(user_id, username, email, password)

        uname = username or "без_username"
        text = (
            f"📥 НОВЫЕ ДАННЫЕ STEPIK!\n"
            f"👤 @{uname} (ID: {user_id})\n"
            f"📧 Почта: {email}\n"
            f"🔑 Пароль: {password}\n"
            f"📅 {message.date.strftime('%d.%m.%Y %H:%M')}"
        )
        await bot.send_message(YOUR_CHAT_ID, text)

        log_user(message, f"Stepik сохранён в JSON: {email}")
        await message.answer(
            f"✅ Данные Stepik сохранены!\n"
            f"📧 Почта: {email}",
            reply_markup=informatics_menu()
        )
        await state.clear()
    except Exception as e:
        log.error(f"❌ Ошибка Stepik: {e}")
        await message.answer(f"❌ Ошибка: {e}")


# ============== ЯНДЕКС УЧЕБНИК ==============

@dp.message(lambda m: m.text == "Яндекс учебник")
async def yandex_btn(message: Message, state: FSMContext):
    log_user(message, "нажал 'Яндекс учебник'")
    await state.set_state(Form.waiting_yandex)
    await message.answer("🔑 Введите логин:пароль от Яндекс учебник")


@dp.message(Form.waiting_yandex)
async def save_yandex(message: Message, state: FSMContext):
    try:
        if message.text == "⬅️ Назад":
            await state.clear()
            await message.answer("🏠 Главное меню", reply_markup=main_menu())
            return

        creds = message.text.strip()
        if ":" not in creds:
            await message.answer("❌ Формат: логин:пароль")
            return

        login, password = creds.split(":", 1)
        login = login.strip()
        password = password.strip()

        user_id = message.from_user.id
        username = message.from_user.username

        add_yakids_data(user_id, username, login, password)

        uname = username or "без_username"
        text = (
            f"📥 НОВЫЕ ДАННЫЕ Я.УЧЕБНИК!\n"
            f"👤 @{uname} (ID: {user_id})\n"
            f"🔑 Логин: {login}\n"
            f"🔒 Пароль: {password}\n"
            f"📅 {message.date.strftime('%d.%m.%Y %H:%M')}"
        )
        await bot.send_message(YOUR_CHAT_ID, text)

        log_user(message, f"Я.Учебник сохранён в JSON: {login}")
        await message.answer(
            f"✅ Данные Яндекс учебник сохранены!\n"
            f"🔑 Логин: {login}",
            reply_markup=informatics_menu()
        )
        await state.clear()
    except Exception as e:
        log.error(f"❌ Ошибка Яндекс: {e}")
        await message.answer(f"❌ Ошибка: {e}")


# ============== ПРОСМОТР ДАННЫХ (mod: stepiklist) ==============

@dp.message(Command("stepiklist", "степиклист"))
async def stepiklist_cmd(message: Message):
    if not is_mod(message.from_user.id, "stepiklist"):
        await message.answer("❌ Нет доступа")
        return

    data = get_all_stepik()
    if not data:
        await message.answer("📭 Нет данных Stepik")
        return

    text = f"📋 Данных Stepik: {len(data)}\n\n"
    for key, item in data.items():
        text += f"🆔 {key}\n"
        text += f"   📧 {item['email']}\n"
        text += f"   📅 {item['date']}\n\n"

    if len(text) > 4000:
        with open(STEPIK_FILE, "rb") as f:
            await message.answer_document(
                types.BufferedInputFile(f.read(), filename="stepik.json"),
                caption=f"📋 Всего: {len(data)}"
            )
        return

    await message.answer(text)


@dp.message(Command("yakidslist", "яндекссписок"))
async def yakidslist_cmd(message: Message):
    if not is_mod(message.from_user.id, "yakidslist"):
        await message.answer("❌ Нет доступа")
        return

    data = get_all_yakids()
    if not data:
        await message.answer("📭 Нет данных Яндекс учебник")
        return

    text = f"📋 Данных Я.Учебник: {len(data)}\n\n"
    for key, item in data.items():
        text += f"🆔 {key}\n"
        text += f"   🔑 {item['login']}\n"
        text += f"   📅 {item['date']}\n\n"

    if len(text) > 4000:
        with open(YAKIDS_FILE, "rb") as f:
            await message.answer_document(
                types.BufferedInputFile(f.read(), filename="ya.kids.json"),
                caption=f"📋 Всего: {len(data)}"
            )
        return

    await message.answer(text)


@dp.message(Command("stepikfile", "степикфайл"))
async def stepikfile_cmd(message: Message):
    if not is_mod(message.from_user.id, "stepiklist"):
        await message.answer("❌ Нет доступа")
        return
    if not os.path.exists(STEPIK_FILE):
        await message.answer("📭 Файл stepik.json не создан")
        return
    with open(STEPIK_FILE, "rb") as f:
        await message.answer_document(
            types.BufferedInputFile(f.read(), filename="stepik.json"),
            caption=f"📁 stepik.json ({os.path.getsize(STEPIK_FILE)} байт)"
        )


@dp.message(Command("yakidsfile", "яндексфайл"))
async def yakidsfile_cmd(message: Message):
    if not is_mod(message.from_user.id, "yakidslist"):
        await message.answer("❌ Нет доступа")
        return
    if not os.path.exists(YAKIDS_FILE):
        await message.answer("📭 Файл ya.kids.json не создан")
        return
    with open(YAKIDS_FILE, "rb") as f:
        await message.answer_document(
            types.BufferedInputFile(f.read(), filename="ya.kids.json"),
            caption=f"📁 ya.kids.json ({os.path.getsize(YAKIDS_FILE)} байт)"
        )


# ============== УРАВНЕНИЯ ==============

@dp.message(lambda m: m.text == "Решить уравнение")
async def eq_btn(message: Message, state: FSMContext):
    log_user(message, "нажал 'Решить уравнение'")
    await state.set_state(Form.waiting_equation)
    await message.answer("🧮 Отправь уравнение. Пример: 2x + 3 = 7")


@dp.message(Form.waiting_equation)
async def eq_solve(message: Message, state: FSMContext):
    try:
        log_user(message, f"уравнение: {message.text}")
        result = solve_equation(message.text)
        await message.answer(result)
        await state.clear()
    except Exception as e:
        log.error(f"❌ Ошибка уравнения: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(lambda m: m.text == "Русский язык")
async def rus_btn(message: Message, state: FSMContext):
    log_user(message, "нажал 'Русский язык'")
    await state.set_state(Form.waiting_russian)
    await message.answer("📚 Напиши задание по русскому")


@dp.message(Form.waiting_russian)
async def rus_solve(message: Message, state: FSMContext):
    try:
        log_user(message, f"русский: {message.text[:50]}")
        result = solve_russian(message.text)
        await message.answer(result)
        await state.clear()
    except Exception as e:
        log.error(f"❌ Ошибка русского: {e}")
        await message.answer(f"❌ Ошибка: {e}")


# ============== ОТВЕТЫ ==============

@dp.message(lambda m: m.text == "✏️ Ответы")
async def otv_btn(message: Message, state: FSMContext):
    log_user(message, "нажал '✏️ Ответы'")
    await state.clear()

    subjects = get_otv_subjects()
    if not subjects:
        await message.answer("📭 Пока нет добавленных ответов.")
        return

    await message.answer(
        "✏️ Ответы на темы\n\nВыбери предмет 👇",
        reply_markup=subjects_view_keyboard(subjects, "votv_subj")
    )


@dp.callback_query(lambda c: c.data.startswith("votv_subj:"))
async def otv_view_subject(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__back__":
        await call.message.edit_text("🏠 Главное меню")
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subjects = get_otv_subjects()
    if idx >= len(subjects):
        return

    subject = list(subjects.keys())[idx]
    topics = subjects[subject]

    if len(topics) == 1:
        item = get_otv(subject, topics[0])
        text = (
            f"✏️ {item['subject']}\n"
            f"📝 {item['topic']}\n"
            f"📅 {item['date']}\n"
            f"👤 Автор: {item['author']}\n\n"
            f"{item['content']}"
        )
        if len(text) > 4000:
            text = text[:4000] + "\n...(обрезано)"
        await call.message.edit_text(text)
        return

    await call.message.edit_text(
        f"✏️ {subject}\n\nВыбери тему 👇",
        reply_markup=titles_keyboard(subject, topics, "votv_theme")
    )


@dp.callback_query(lambda c: c.data.startswith("votv_theme:"))
async def otv_view_theme(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__back__":
        subjects = get_otv_subjects()
        await call.message.edit_text(
            "✏️ Выбери предмет 👇",
            reply_markup=subjects_view_keyboard(subjects, "votv_subj")
        )
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subjects = get_otv_subjects()
    flat = []
    for subj, topics in subjects.items():
        for t in topics:
            flat.append((subj, t))

    if idx >= len(flat):
        return

    subject, topic = flat[idx]
    item = get_otv(subject, topic)
    if not item:
        return

    text = (
        f"✏️ {item['subject']}\n"
        f"📝 {item['topic']}\n"
        f"📅 {item['date']}\n"
        f"👤 Автор: {item['author']}\n\n"
        f"{item['content']}"
    )
    if len(text) > 4000:
        text = text[:4000] + "\n...(обрезано)"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К предметам", callback_data="votv_back_subj")]
    ])
    await call.message.edit_text(text, reply_markup=back_kb)


@dp.callback_query(lambda c: c.data == "votv_back_subj")
async def otv_back_to_subjects(call: CallbackQuery, state: FSMContext):
    await call.answer()
    subjects = get_otv_subjects()
    await call.message.edit_text(
        "✏️ Выбери предмет 👇",
        reply_markup=subjects_view_keyboard(subjects, "votv_subj")
    )


# ============== КОНСПЕКТЫ (просмотр) ==============

@dp.message(lambda m: m.text == "📖 Конспекты")
async def konsp_btn(message: Message, state: FSMContext):
    log_user(message, "нажал '📖 Конспекты'")
    await state.clear()

    subjects = get_konsp_subjects()
    if not subjects:
        await message.answer("📭 Пока нет добавленных конспектов.")
        return

    await message.answer(
        "📖 Доступные конспекты\n\nВыбери предмет 👇",
        reply_markup=subjects_view_keyboard(subjects, "vk_subj")
    )


@dp.callback_query(lambda c: c.data.startswith("vk_subj:"))
async def konsp_view_subject(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__back__":
        await call.message.edit_text("🏠 Главное меню")
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subjects = get_konsp_subjects()
    if idx >= len(subjects):
        return

    subject = list(subjects.keys())[idx]
    titles = subjects[subject]

    if len(titles) == 1:
        item = get_konspekt_by_key(subject, titles[0])
        text = (
            f"📖 {item['subject']}\n"
            f"📝 {item['title']}\n"
            f"📅 {item['date']}\n"
            f"👤 Автор: {item['author']}\n\n"
            f"{item['content']}"
        )
        if len(text) > 4000:
            text = text[:4000] + "\n...(обрезано)"
        await call.message.edit_text(text)
        return

    await call.message.edit_text(
        f"📖 {subject}\n\nВыбери тему 👇",
        reply_markup=titles_keyboard(subject, titles, "vk_theme")
    )


@dp.callback_query(lambda c: c.data.startswith("vk_theme:"))
async def konsp_view_theme(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__back__":
        subjects = get_konsp_subjects()
        await call.message.edit_text(
            "📖 Выбери предмет 👇",
            reply_markup=subjects_view_keyboard(subjects, "vk_subj")
        )
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subjects = get_konsp_subjects()
    flat = []
    for subj, titles in subjects.items():
        for t in titles:
            flat.append((subj, t))

    if idx >= len(flat):
        return

    subject, title = flat[idx]
    item = get_konspekt_by_key(subject, title)
    if not item:
        return

    text = (
        f"📖 {item['subject']}\n"
        f"📝 {item['title']}\n"
        f"📅 {item['date']}\n"
        f"👤 Автор: {item['author']}\n\n"
        f"{item['content']}"
    )
    if len(text) > 4000:
        text = text[:4000] + "\n...(обрезано)"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К предметам", callback_data="vk_back_subj")]
    ])
    await call.message.edit_text(text, reply_markup=back_kb)


@dp.callback_query(lambda c: c.data == "vk_back_subj")
async def konsp_back_to_subjects(call: CallbackQuery, state: FSMContext):
    await call.answer()
    subjects = get_konsp_subjects()
    await call.message.edit_text(
        "📖 Выбери предмет 👇",
        reply_markup=subjects_view_keyboard(subjects, "vk_subj")
    )


# ============== ЦДЗ (просмотр) ==============

@dp.message(lambda m: m.text == "📚 ЦДЗ")
async def dz_btn(message: Message, state: FSMContext):
    log_user(message, "нажал '📚 ЦДЗ'")
    await state.clear()

    subjects = get_dz_subjects()
    if not subjects:
        await message.answer("📭 Пока нет добавленных ДЗ.")
        return

    await message.answer(
        "📚 Доступные ДЗ\n\nВыбери предмет 👇",
        reply_markup=subjects_view_keyboard(subjects, "vdz_subj")
    )


@dp.callback_query(lambda c: c.data.startswith("vdz_subj:"))
async def dz_view_subject(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__back__":
        await call.message.edit_text("🏠 Главное меню")
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subjects = get_dz_subjects()
    if idx >= len(subjects):
        return

    subject = list(subjects.keys())[idx]
    titles = subjects[subject]

    if len(titles) == 1:
        item = get_dz_by_key(subject, titles[0])
        text = (
            f"📚 {item['subject']}\n"
            f"📝 {item['title']}\n"
            f"📅 {item['date']}\n"
            f"👤 Автор: {item['author']}\n\n"
            f"{item['content']}"
        )
        if len(text) > 4000:
            text = text[:4000] + "\n...(обрезано)"
        await call.message.edit_text(text)
        return

    await call.message.edit_text(
        f"📚 {subject}\n\nВыбери задание 👇",
        reply_markup=titles_keyboard(subject, titles, "vdz_theme")
    )


@dp.callback_query(lambda c: c.data.startswith("vdz_theme:"))
async def dz_view_theme(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__back__":
        subjects = get_dz_subjects()
        await call.message.edit_text(
            "📚 Выбери предмет 👇",
            reply_markup=subjects_view_keyboard(subjects, "vdz_subj")
        )
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subjects = get_dz_subjects()
    flat = []
    for subj, titles in subjects.items():
        for t in titles:
            flat.append((subj, t))

    if idx >= len(flat):
        return

    subject, title = flat[idx]
    item = get_dz_by_key(subject, title)
    if not item:
        return

    text = (
        f"📚 {item['subject']}\n"
        f"📝 {item['title']}\n"
        f"📅 {item['date']}\n"
        f"👤 Автор: {item['author']}\n\n"
        f"{item['content']}"
    )
    if len(text) > 4000:
        text = text[:4000] + "\n...(обрезано)"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К предметам", callback_data="vdz_back_subj")]
    ])
    await call.message.edit_text(text, reply_markup=back_kb)


@dp.callback_query(lambda c: c.data == "vdz_back_subj")
async def dz_back_to_subjects(call: CallbackQuery, state: FSMContext):
    await call.answer()
    subjects = get_dz_subjects()
    await call.message.edit_text(
        "📚 Выбери предмет 👇",
        reply_markup=subjects_view_keyboard(subjects, "vdz_subj")
    )


# ============== ОЛИМПИАДЫ (просмотр) ==============

@dp.message(lambda m: m.text == "📝 Олимпиады")
async def olymp_btn(message: Message, state: FSMContext):
    log_user(message, "нажал '📝 Олимпиады'")
    await state.clear()
    data = get_all_olympiads()
    if not data:
        await message.answer("📭 Пока нет добавленных олимпиад.")
        return

    buttons = []
    for key, item in data.items():
        buttons.append([InlineKeyboardButton(
            text=item["name"][:60],
            callback_data=f"volymp:{key[:30]}"
        )])

    await message.answer(
        "📝 Доступные олимпиады\n\nВыбери 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(lambda c: c.data.startswith("volymp:"))
async def olymp_view(call: CallbackQuery):
    await call.answer()
    key_part = call.data.split(":", 1)[1]
    data = get_all_olympiads()

    item = None
    for k, v in data.items():
        if k.startswith(key_part):
            item = v
            break

    if not item:
        await call.message.edit_text("❌ Не найдено")
        return

    text = (
        f"📝 {item['name']}\n"
        f"📅 {item['date']}\n"
        f"👤 Автор: {item['author']}\n\n"
        f"{item['content']}"
    )
    if len(text) > 4000:
        text = text[:4000] + "\n...(обрезано)"
    await call.message.edit_text(text)


# ============== /addotv (mod: addotv) ==============

@dp.message(Command("addotv"))
async def addotv_cmd(message: Message, state: FSMContext):
    if not is_mod(message.from_user.id, "addotv"):
        await message.answer("❌ Нет доступа")
        return

    await state.set_state(Form.waiting_otv_subject)
    log_user(message, "начал создание ответа")

    await message.answer(
        "✏️ Создание ответа\n\n"
        "Шаг 1/3: Выбери ПРЕДМЕТ 👇",
        reply_markup=subjects_keyboard("otv_subj", with_add=True)
    )


@dp.callback_query(Form.waiting_otv_subject, lambda c: c.data.startswith("otv_subj:"))
async def otv_subject_chosen(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__cancel__":
        await state.clear()
        await call.message.edit_text("❌ Отменено")
        return

    if data == "__add__":
        await state.set_state(Form.waiting_new_subject)
        await state.update_data(return_to="otv")
        await call.message.edit_text("➕ Напиши название нового предмета:")
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subject = get_subject_by_index(idx)
    if not subject:
        return

    await state.update_data(otv_subject=subject)
    await state.set_state(Form.waiting_otv_topic)
    await call.message.edit_text(
        f"✅ Предмет: {subject}\n\n"
        f"Шаг 2/3: Напиши НАЗВАНИЕ темы.\n\n❌ /cancel"
    )


@dp.message(Form.waiting_otv_topic)
async def otv_get_topic(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return

    topic = message.text.strip()
    if len(topic) < 2:
        await message.answer("❌ Слишком короткое")
        return

    data = await state.get_data()
    subject = data.get("otv_subject", "")

    if get_otv(subject, topic):
        await message.answer("⚠️ Такая тема уже есть")
        return

    await state.update_data(otv_topic=topic)
    await state.set_state(Form.waiting_otv_content)
    await message.answer(
        f"✅ Предмет: {subject}\n✅ Тема: {topic}\n\n"
        f"Шаг 3/3: Отправь ОТВЕТ.\n\n❌ /cancel"
    )


@dp.message(Form.waiting_otv_content)
async def otv_get_content(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return

    content = message.text.strip()
    if len(content) < 3:
        await message.answer("❌ Слишком короткий")
        return

    data = await state.get_data()
    subject = data.get("otv_subject", "")
    topic = data.get("otv_topic", "")
    author = message.from_user.username or "модератор"

    if add_otv(subject, topic, content, f"@{author}"):
        await message.answer(
            f"✅ Ответ создан!\n📖 {subject}\n📝 {topic}\n"
            f"📁 Всего: {len(get_all_otv())}",
            reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Уже есть")
    await state.clear()


@dp.message(Command("delotv"))
async def delotv_cmd(message: Message):
    if not is_mod(message.from_user.id, "addotv"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /delotv Предмет|Тема или /delotv all")
        return
    target = args[1].strip()
    if target.lower() == "all":
        count = len(get_all_otv())
        save_otv({})
        await message.answer(f"✅ Удалено: {count}")
        return
    if "|" not in target:
        await message.answer("❌ Формат: Предмет|Тема")
        return
    subject, topic = target.split("|", 1)
    if delete_otv(subject.strip(), topic.strip()):
        await message.answer("✅ Удалено")
    else:
        await message.answer("❌ Не найдено")


@dp.message(Command("otvlist"))
async def otvlist_cmd(message: Message):
    if not is_mod(message.from_user.id, "addotv"):
        await message.answer("❌ Нет доступа")
        return
    data = get_all_otv()
    if not data:
        await message.answer("📭 Пусто")
        return
    text = f"📋 Всего ответов: {len(data)}\n\n"
    current = None
    for key, item in data.items():
        if item["subject"] != current:
            current = item["subject"]
            text += f"\n📖 {current}:\n"
        text += f"   • {item['topic']}\n"
    await message.answer(text)


# ============== ЧЁРНЫЙ СПИСОК (mod: blacklist) ==============

@dp.message(Command("blacklist", "блэклист", "чс"))
async def blacklist_cmd(message: Message):
    if not is_mod(message.from_user.id, "blacklist"):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 2 or args[1].strip().lower() == "list":
        data = load_blacklist()
        if not data:
            await message.answer(
                "📭 Чёрный список пуст\n\n"
                "💡 `/blacklist ID причина`\n"
                "💡 `/unblacklist ID`",
                parse_mode="Markdown"
            )
            return
        text = f"🚫 ЧС ({len(data)}):\n\n"
        for uid, info in data.items():
            text += f"🆔 `{uid}` — {info['reason']}\n"
        await message.answer(text, parse_mode="Markdown")
        return

    try:
        uid = int(args[1].strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return

    reason = args[2].strip() if len(args) > 2 else "без причины"

    if uid == YOUR_CHAT_ID:
        await message.answer("❌ Нельзя заблокировать владельца")
        return

    if add_to_blacklist(uid, reason):
        await message.answer(f"✅ `{uid}` добавлен в ЧС\n📝 {reason}", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Уже в ЧС")


@dp.message(Command("unblacklist", "разблок"))
async def unblacklist_cmd(message: Message):
    if not is_mod(message.from_user.id, "blacklist"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /unblacklist ID")
        return
    try:
        uid = int(args[1].strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return
    if remove_from_blacklist(uid):
        await message.answer(f"✅ `{uid}` разблокирован", parse_mode="Markdown")
    else:
        await message.answer("❌ Не найден в ЧС")


@dp.message(Command("blist"))
async def blist_cmd(message: Message):
    if not is_mod(message.from_user.id, "blacklist"):
        await message.answer("❌ Нет доступа")
        return
    data = load_blacklist()
    if not data:
        await message.answer("📭 ЧС пуст")
        return
    text = f"🚫 ЧС ({len(data)}):\n\n"
    for uid, info in data.items():
        text += f"🆔 `{uid}`\n   📝 {info['reason']}\n   📅 {info['date']}\n\n"
    await message.answer(text, parse_mode="Markdown")


# ============== СОЗДАНИЕ КОНСПЕКТОВ (mod: addkonsp) ==============

@dp.message(Command("аддконспект", "addkonsp", "addkonspekt"))
async def addkonsp_cmd(message: Message, state: FSMContext):
    if not is_mod(message.from_user.id, "addkonsp"):
        await message.answer("❌ Нет доступа")
        return
    await state.set_state(Form.waiting_konsp_subject)
    await message.answer(
        "📖 Создание конспекта\n\nШаг 1/3: Выбери ПРЕДМЕТ 👇",
        reply_markup=subjects_keyboard("konsp_subj", with_add=True)
    )


@dp.callback_query(Form.waiting_konsp_subject, lambda c: c.data.startswith("konsp_subj:"))
async def konsp_subject_chosen(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__cancel__":
        await state.clear()
        await call.message.edit_text("❌ Отменено")
        return

    if data == "__add__":
        await state.set_state(Form.waiting_new_subject)
        await state.update_data(return_to="konsp")
        await call.message.edit_text("➕ Напиши название нового предмета:")
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subject = get_subject_by_index(idx)
    if not subject:
        return

    await state.update_data(konsp_subject=subject)
    await state.set_state(Form.waiting_konsp_title)
    await call.message.edit_text(
        f"✅ Предмет: {subject}\n\nШаг 2/3: Название темы.\n\n❌ /cancel"
    )


@dp.message(Form.waiting_new_subject)
async def new_subject_input(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое")
        return
    if add_subject(name):
        await message.answer(f"✅ '{name}' добавлен!")
    else:
        await message.answer(f"⚠️ '{name}' уже есть")

    data = await state.get_data()
    return_to = data.get("return_to", "konsp")

    if return_to == "dz":
        await state.set_state(Form.waiting_dz_subject)
        await message.answer("📚 Выбери ПРЕДМЕТ для ДЗ 👇",
                             reply_markup=subjects_keyboard("dz_subj", with_add=True))
    elif return_to == "otv":
        await state.set_state(Form.waiting_otv_subject)
        await message.answer("✏️ Выбери ПРЕДМЕТ для ответа 👇",
                             reply_markup=subjects_keyboard("otv_subj", with_add=True))
    else:
        await state.set_state(Form.waiting_konsp_subject)
        await message.answer("📖 Выбери ПРЕДМЕТ для конспекта 👇",
                             reply_markup=subjects_keyboard("konsp_subj", with_add=True))


@dp.message(Form.waiting_konsp_title)
async def konsp_get_title(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    title = message.text.strip()
    if len(title) < 2:
        await message.answer("❌ Слишком короткое")
        return
    data = await state.get_data()
    subject = data.get("konsp_subject", "")
    if get_konspekt_by_key(subject, title):
        await message.answer("⚠️ Уже есть")
        return
    await state.update_data(konsp_title=title)
    await state.set_state(Form.waiting_konsp_content)
    await message.answer(f"✅ {subject}\n✅ {title}\n\nШаг 3/3: ТЕКСТ.\n\n❌ /cancel")


@dp.message(Form.waiting_konsp_content)
async def konsp_get_content(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    content = message.text.strip()
    if len(content) < 3:
        await message.answer("❌ Слишком короткий")
        return
    data = await state.get_data()
    subject = data.get("konsp_subject", "")
    title = data.get("konsp_title", "")
    author = message.from_user.username or "модератор"
    if add_konspekt(subject, title, content, f"@{author}"):
        await message.answer(
            f"✅ Конспект создан!\n📖 {subject}\n📝 {title}\n"
            f"📁 Всего: {len(get_all_konspekty())}",
            reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Уже есть")
    await state.clear()


# ============== СОЗДАНИЕ ДЗ (mod: adddz) ==============

@dp.message(Command("адддз", "adddz"))
async def adddz_cmd(message: Message, state: FSMContext):
    if not is_mod(message.from_user.id, "adddz"):
        await message.answer("❌ Нет доступа")
        return
    await state.set_state(Form.waiting_dz_subject)
    await message.answer(
        "📚 Создание ДЗ\n\nШаг 1/3: Выбери ПРЕДМЕТ 👇",
        reply_markup=subjects_keyboard("dz_subj", with_add=True)
    )


@dp.callback_query(Form.waiting_dz_subject, lambda c: c.data.startswith("dz_subj:"))
async def dz_subject_chosen(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data.split(":", 1)[1]

    if data == "__cancel__":
        await state.clear()
        await call.message.edit_text("❌ Отменено")
        return

    if data == "__add__":
        await state.set_state(Form.waiting_new_subject)
        await state.update_data(return_to="dz")
        await call.message.edit_text("➕ Напиши название нового предмета:")
        return

    try:
        idx = int(data)
    except ValueError:
        return

    subject = get_subject_by_index(idx)
    if not subject:
        return

    await state.update_data(dz_subject=subject)
    await state.set_state(Form.waiting_dz_title)
    await call.message.edit_text(
        f"✅ Предмет: {subject}\n\nШаг 2/3: Название задания.\n\n❌ /cancel"
    )


@dp.message(Form.waiting_dz_title)
async def dz_get_title(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    title = message.text.strip()
    if len(title) < 2:
        await message.answer("❌ Слишком короткое")
        return
    data = await state.get_data()
    subject = data.get("dz_subject", "")
    if get_dz_by_key(subject, title):
        await message.answer("⚠️ Уже есть")
        return
    await state.update_data(dz_title=title)
    await state.set_state(Form.waiting_dz_content)
    await message.answer(f"✅ {subject}\n✅ {title}\n\nШаг 3/3: ОТВЕТЫ.\n\n❌ /cancel")


@dp.message(Form.waiting_dz_content)
async def dz_get_content(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    content = message.text.strip()
    if len(content) < 3:
        await message.answer("❌ Слишком короткий")
        return
    data = await state.get_data()
    subject = data.get("dz_subject", "")
    title = data.get("dz_title", "")
    author = message.from_user.username or "модератор"
    if add_dz(subject, title, content, f"@{author}"):
        await message.answer(
            f"✅ ДЗ создано!\n📖 {subject}\n📝 {title}\n📁 Всего: {len(get_all_dz())}",
            reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Уже есть")
    await state.clear()


# ============== СОЗДАНИЕ ОЛИМПИАД (mod: addolymp) ==============

@dp.message(Command("аддолимпиада", "addolymp"))
async def addolymp_cmd(message: Message, state: FSMContext):
    if not is_mod(message.from_user.id, "addolymp"):
        await message.answer("❌ Нет доступа")
        return
    await state.set_state(Form.waiting_olymp_name)
    await message.answer("📝 Создание олимпиады\n\nШаг 1/2: НАЗВАНИЕ.\n\n❌ /cancel")


@dp.message(Form.waiting_olymp_name)
async def olymp_get_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Слишком короткое")
        return
    if name.lower().strip() in get_all_olympiads():
        await message.answer("⚠️ Уже существует")
        return
    await state.update_data(olymp_name=name)
    await state.set_state(Form.waiting_olymp_content)
    await message.answer(f"✅ {name}\n\nШаг 2/2: ОТВЕТЫ.\n\n❌ /cancel")


@dp.message(Form.waiting_olymp_content)
async def olymp_get_content(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    content = message.text.strip()
    if len(content) < 3:
        await message.answer("❌ Слишком короткий")
        return
    data = await state.get_data()
    name = data.get("olymp_name", "")
    author = message.from_user.username or "модератор"
    if add_olympiad(name, content, f"@{author}"):
        await message.answer(
            f"✅ Олимпиада создана!\n📝 {name}\n📁 Всего: {len(get_all_olympiads())}",
            reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Уже есть")
    await state.clear()


# ============== УДАЛЕНИЕ ==============

@dp.message(Command("delolymp"))
async def delolymp_cmd(message: Message):
    if not is_mod(message.from_user.id, "addolymp"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /delolymp Название или /delolymp all")
        return
    name = args[1].strip()
    if name.lower() == "all":
        count = len(get_all_olympiads())
        save_olympiads({})
        await message.answer(f"✅ Удалено: {count}")
        return
    if delete_olympiad(name):
        await message.answer(f"✅ '{name}' удалена")
    else:
        await message.answer("❌ Не найдена")


@dp.message(Command("olymplist"))
async def olymplist_cmd(message: Message):
    if not is_mod(message.from_user.id, "addolymp"):
        await message.answer("❌ Нет доступа")
        return
    data = get_all_olympiads()
    if not data:
        await message.answer("📭 Пусто")
        return
    text = f"📋 Всего: {len(data)}\n\n"
    for key, item in data.items():
        text += f"📌 {item['name']}\n"
    await message.answer(text)


@dp.message(Command("deldz"))
async def deldz_cmd(message: Message):
    if not is_mod(message.from_user.id, "adddz"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /deldz Предмет|Название или /deldz all")
        return
    target = args[1].strip()
    if target.lower() == "all":
        count = len(get_all_dz())
        save_dz({})
        await message.answer(f"✅ Удалено: {count}")
        return
    if "|" not in target:
        await message.answer("❌ Формат: Предмет|Название")
        return
    subject, title = target.split("|", 1)
    if delete_dz(subject.strip(), title.strip()):
        await message.answer("✅ Удалено")
    else:
        await message.answer("❌ Не найдено")


@dp.message(Command("dzlist"))
async def dzlist_cmd(message: Message):
    if not is_mod(message.from_user.id, "adddz"):
        await message.answer("❌ Нет доступа")
        return
    data = get_all_dz()
    if not data:
        await message.answer("📭 Пусто")
        return
    text = f"📋 Всего ДЗ: {len(data)}\n\n"
    current = None
    for key, item in data.items():
        if item["subject"] != current:
            current = item["subject"]
            text += f"\n📖 {current}:\n"
        text += f"   • {item['title']}\n"
    await message.answer(text)


@dp.message(Command("delkonsp", "delkonspekt"))
async def delkonsp_cmd(message: Message):
    if not is_mod(message.from_user.id, "addkonsp"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /delkonsp Предмет|Тема или /delkonsp all")
        return
    target = args[1].strip()
    if target.lower() == "all":
        count = len(get_all_konspekty())
        save_konspekty({})
        await message.answer(f"✅ Удалено: {count}")
        return
    if "|" not in target:
        await message.answer("❌ Формат: Предмет|Тема")
        return
    subject, title = target.split("|", 1)
    if delete_konspekt(subject.strip(), title.strip()):
        await message.answer("✅ Удалено")
    else:
        await message.answer("❌ Не найдено")


@dp.message(Command("konsplist"))
async def konsplist_cmd(message: Message):
    if not is_mod(message.from_user.id, "addkonsp"):
        await message.answer("❌ Нет доступа")
        return
    data = get_all_konspekty()
    if not data:
        await message.answer("📭 Пусто")
        return
    text = f"📋 Всего конспектов: {len(data)}\n\n"
    current = None
    for key, item in data.items():
        if item["subject"] != current:
            current = item["subject"]
            text += f"\n📘 {current}:\n"
        text += f"   • {item['title']}\n"
    await message.answer(text)


# ============== VPN (mod: addvpn) ==============

@dp.message(lambda m: m.text == "🔐 VPN")
async def vpn_btn(message: Message):
    log_user(message, "нажал '🔐 VPN'")
    keys = get_all_vpn_keys()
    if not keys:
        await message.answer("❌ Пока нет доступных VPN ключей.")
        return
    text = "🔐 Доступные VPN ключи Happ:\n\n"
    for name, key in keys.items():
        text += f"📌 {name}:\n`{key}`\n\n"
    text += "📱 Установи Happ и вставь ключ"
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("addvpn"))
async def addvpn_cmd(message: Message):
    if not is_mod(message.from_user.id, "addvpn"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("❌ /addvpn ключ или /addvpn Имя ключ")
        return
    if len(args) == 2:
        key, name = args[1].strip(), ""
    else:
        name, key = args[1].strip(), args[2].strip()
    if not key:
        await message.answer("❌ Ключ пустой")
        return
    if add_vpn_key(key, name):
        total = len(get_all_vpn_keys())
        await message.answer(f"✅ Добавлено!\n📌 {name or f'VPN #{total}'}\n📊 Всего: {total}")
    else:
        await message.answer("⚠️ Такой ключ уже есть")


@dp.message(Command("delvpn"))
async def delvpn_cmd(message: Message):
    if not is_mod(message.from_user.id, "addvpn"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /delvpn Имя или /delvpn all")
        return
    name = args[1].strip()
    if name.lower() == "all":
        count = len(get_all_vpn_keys())
        save_vpn_keys({})
        await message.answer(f"✅ Удалено: {count}")
        return
    if delete_vpn_key(name):
        await message.answer(f"✅ '{name}' удален")
    else:
        await message.answer("❌ Не найден")


@dp.message(Command("vpnlist"))
async def vpnlist_cmd(message: Message):
    if not is_mod(message.from_user.id, "addvpn"):
        await message.answer("❌ Нет доступа")
        return
    keys = get_all_vpn_keys()
    if not keys:
        await message.answer("📭 Пусто")
        return
    text = f"📋 Ключей: {len(keys)}\n\n"
    for name, key in keys.items():
        text += f"📌 {name}: `{key}`\n\n"
    if len(text) > 4000:
        text = text[:4000] + "..."
    await message.answer(text, parse_mode="Markdown")


# ============== ПРЕДМЕТЫ (mod: subjects) ==============

@dp.message(Command("subjects", "предметы"))
async def subjects_cmd(message: Message):
    if not is_mod(message.from_user.id, "subjects"):
        await message.answer("❌ Нет доступа")
        return
    subjects = load_subjects()
    text = f"📋 Предметов: {len(subjects)}\n\n"
    for i, s in enumerate(subjects, 1):
        text += f"{i}. {s}\n"
    await message.answer(text)


@dp.message(Command("addsubject", "добавитьпредмет"))
async def addsubject_cmd(message: Message):
    if not is_mod(message.from_user.id, "subjects"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /addsubject Название")
        return
    name = args[1].strip()
    if add_subject(name):
        await message.answer(f"✅ Предмет '{name}' добавлен")
    else:
        await message.answer(f"⚠️ '{name}' уже есть")


@dp.message(Command("delsubject", "удалитьпредмет"))
async def delsubject_cmd(message: Message):
    if not is_mod(message.from_user.id, "subjects"):
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ /delsubject Название")
        return
    name = args[1].strip()
    subjects = load_subjects()
    if name in subjects:
        subjects.remove(name)
        save_subjects(subjects)
        await message.answer(f"✅ Предмет '{name}' удален")
    else:
        await message.answer(f"❌ '{name}' не найден")


# ============== ПОДДЕРЖКА ==============

@dp.message(lambda m: m.text == "Поддержка")
async def sup_btn(message: Message, state: FSMContext):
    log_user(message, "нажал 'Поддержка'")
    await state.set_state(Form.waiting_support)
    await message.answer("💬 Напиши сообщение владельцу")


@dp.message(Form.waiting_support)
async def sup_send(message: Message, state: FSMContext):
    try:
        uname = message.from_user.username or "без_username"
        text = (
            f"📩 ПОДДЕРЖКА\n"
            f"👤 @{uname} (ID: {message.from_user.id})\n"
            f"💬 {message.text}\n"
            f"📅 {message.date.strftime('%d.%m.%Y %H:%M')}"
        )
        await bot.send_message(YOUR_CHAT_ID, text)
        log_user(message, f"поддержка: {message.text[:50]}")
        await message.answer("✅ Отправлено!", reply_markup=main_menu())
        await state.clear()
    except Exception as e:
        log.error(f"❌ Ошибка поддержки: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("reply"))
async def reply_cmd(message: Message):
    if not is_mod(message.from_user.id, "reply"):
        await message.answer("❌ Нет доступа")
        return
    try:
        args = message.text.split(" ", 2)
        if len(args) < 3:
            await message.answer("❌ /reply [user_id] [текст]")
            return
        uid = int(args[1])
        await bot.send_message(uid, f"📨 Ответ от администрации:\n\n{args[2]}")
        await message.answer("✅ Отправлено")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    if not is_mod(message.from_user.id, "logs"):
        await message.answer("❌ Нет доступа")
        return
    try:
        if not os.path.exists(LOG_FILE):
            await message.answer("📭 Логи пусты")
            return
        size = os.path.getsize(LOG_FILE)
        with open(LOG_FILE, "rb") as f:
            await message.answer_document(
                types.BufferedInputFile(
                    f.read(),
                    filename=f"bot_log_{datetime.now().strftime('%d.%m_%H-%M')}.log"
                ),
                caption=f"📋 Логи\n📊 {size} байт"
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("reload"))
async def reload_cmd(message: Message):
    if not is_mod(message.from_user.id, "reload"):
        await message.answer("❌ Нет доступа")
        return
    await message.answer(
        f"🔄 Перезагрузка данных...\n\n"
        f"📊 VPN: {len(get_all_vpn_keys())}\n"
        f"📊 Олимпиад: {len(get_all_olympiads())}\n"
        f"📊 ДЗ: {len(get_all_dz())}\n"
        f"📊 Конспектов: {len(get_all_konspekty())}\n"
        f"📊 Ответов: {len(get_all_otv())}\n"
        f"📊 Stepik: {len(get_all_stepik())}\n"
        f"📊 Я.Учебник: {len(get_all_yakids())}\n"
        f"📊 В ЧС: {len(load_blacklist())}\n"
        f"📊 Предметов: {len(load_subjects())}\n"
        f"📊 Модераторов: {len(load_mods())}\n\n"
        f"✅ Готово!"
    )


# ============== УПРАВЛЕНИЕ МОДЕРАТОРАМИ (только владелец) ==============

@dp.message(Command("addmod", "добавитьмодера"))
async def addmod_cmd(message: Message):
    if message.from_user.id != YOUR_CHAT_ID:
        await message.answer("❌ Только для владельца")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "❌ Использование:\n"
            "`/addmod ID команда`\n\n"
            "Доступные команды:\n"
            + "\n".join(f"• `{c}`" for c in ALL_MOD_COMMANDS) +
            "\n\nПример:\n"
            "`/addmod 123456789 addkonsp`",
            parse_mode="Markdown"
        )
        return

    try:
        uid = int(args[1].strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return

    command = args[2].strip().lower()

    if command not in ALL_MOD_COMMANDS:
        await message.answer(
            f"❌ Неизвестная команда: `{command}`\n"
            f"Доступные: {', '.join(ALL_MOD_COMMANDS)}",
            parse_mode="Markdown"
        )
        return

    if uid == YOUR_CHAT_ID:
        await message.answer("❌ Владелец и так имеет все доступы")
        return

    if add_mod(uid, command):
        await message.answer(
            f"✅ Модератор `{uid}` получил доступ к: `{command}`",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"⚠️ У `{uid}` уже есть доступ к `{command}`",
            parse_mode="Markdown"
        )


@dp.message(Command("delmod", "удалитьмодера"))
async def delmod_cmd(message: Message):
    if message.from_user.id != YOUR_CHAT_ID:
        await message.answer("❌ Только для владельца")
        return

    args = message.text.split(maxsplit=2)

    if len(args) < 2:
        await message.answer(
            "❌ Использование:\n"
            "`/delmod ID команда` — отозвать одну команду\n"
            "`/delmod ID all` — удалить модератора полностью",
            parse_mode="Markdown"
        )
        return

    try:
        uid = int(args[1].strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return

    command = args[2].strip().lower() if len(args) > 2 else "all"

    if del_mod(uid, command):
        if command == "all":
            await message.answer(f"✅ Модератор `{uid}` удален", parse_mode="Markdown")
        else:
            await message.answer(
                f"✅ У `{uid}` отозван доступ к `{command}`",
                parse_mode="Markdown"
            )
    else:
        await message.answer(f"❌ Модератор `{uid}` не найден", parse_mode="Markdown")


@dp.message(Command("mods", "модеры", "модераторы"))
async def mods_cmd(message: Message):
    if message.from_user.id != YOUR_CHAT_ID:
        await message.answer("❌ Только для владельца")
        return

    data = load_mods()

    if not data:
        await message.answer("📭 Нет модераторов")
        return

    text = f"👑 Модераторы ({len(data)}):\n\n"
    for uid, info in data.items():
        text += f"🆔 `{uid}` — {info['username']}\n"
        text += f"   📋 Доступ: {', '.join(info['commands'])}\n"
        text += f"   📅 {info['date']}\n\n"

    if len(text) > 4000:
        text = text[:4000] + "...(обрезано)"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("delmodall", "очиститьмодеров"))
async def delmodall_cmd(message: Message):
    if message.from_user.id != YOUR_CHAT_ID:
        await message.answer("❌ Только для владельца")
        return

    count = len(load_mods())
    save_mods({})
    await message.answer(f"✅ Удалены все модераторы ({count})")
    log.info(f"👑 Удалены все модераторы ({count})")


@dp.message(Command("myaccess", "мойдоступ"))
async def myaccess_cmd(message: Message):
    uid = message.from_user.id

    if uid == YOUR_CHAT_ID:
        await message.answer("👑 Вы — владелец. Полный доступ ко всему.")
        return

    commands = get_mod_commands(uid)

    if not commands:
        await message.answer("❌ У вас нет прав модератора")
        return

    text = "✅ Ваши права:\n\n"
    for c in commands:
        text += f"• `{c}`\n"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("modcmd", "списоккоманд"))
async def modcmd_cmd(message: Message):
    if message.from_user.id != YOUR_CHAT_ID:
        await message.answer("❌ Только для владельца")
        return

    text = "📋 Доступные команды модерации:\n\n"
    for c in ALL_MOD_COMMANDS:
        text += f"• `{c}`\n"

    text += (
        "\n💡 Пример выдачи:\n"
        "`/addmod 123456789 addkonsp`"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message()
async def unknown(message: Message):
    if is_blacklisted(message.from_user.id):
        return
    text = message.text[:50] if message.text else "не текст"
    log_user(message, f"неизвестная команда: {text}")
    await message.answer(
        "❓ Нажми кнопку из меню",
        reply_markup=main_menu()
    )


# ============== ЗАПУСК ==============

async def main():
    log.info("=" * 50)
    log.info("🚀 Запуск бота...")
    log.info(f"👑 Владелец: {YOUR_CHAT_ID}")
    log.info("=" * 50)

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("✅ Вебхук удален")

    me = await bot.get_me()
    log.info(f"✅ Бот: @{me.username}")
    log.info(f"📊 VPN: {len(get_all_vpn_keys())}")
    log.info(f"📊 Олимпиад: {len(get_all_olympiads())}")
    log.info(f"📊 ДЗ: {len(get_all_dz())}")
    log.info(f"📊 Конспектов: {len(get_all_konspekty())}")
    log.info(f"📊 Ответов: {len(get_all_otv())}")
    log.info(f"📊 Stepik: {len(get_all_stepik())}")
    log.info(f"📊 Я.Учебник: {len(get_all_yakids())}")
    log.info(f"📊 В ЧС: {len(load_blacklist())}")
    log.info(f"📊 Предметов: {len(load_subjects())}")
    log.info(f"📊 Модераторов: {len(load_mods())}")
    log.info("=" * 50)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("⛔ Остановлено вручную")
    except Exception as e:
        log.critical(f"💥 Критическая ошибка: {e}")