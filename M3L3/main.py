# main.py
import os
from telebot import TeleBot, types
from telebot.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

from logic import DB_Manager
from config import TOKEN, DATABASE

# ========== Инициализация ==========
bot = TeleBot(TOKEN)
manager = DB_Manager(DATABASE)
os.makedirs("project_photos", exist_ok=True)

hide_board = types.ReplyKeyboardRemove()
cancel_button = "Отмена 🚫"

# ========== Вспомогательные функции ==========

def cancel(message):
    """Скрыть клавиатуру и подсказать /info."""
    bot.send_message(
        message.chat.id,
        "Чтобы посмотреть команды, используй: /info",
        reply_markup=hide_board
    )

def no_projects(message):
    """Сообщение, если проектов нет."""
    bot.send_message(
        message.chat.id,
        "У тебя пока нет проектов!\nДобавь их командой /new_project"
    )

def gen_reply_markup(options: list[str]) -> ReplyKeyboardMarkup:
    """
    Reply-клавиатура:
    - one_time_keyboard=True → исчезает после первого нажатия
    - resize_keyboard=True → оптимальный размер
    """
    markup = ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True
    )
    for o in options:
        markup.add(KeyboardButton(o))
    markup.add(KeyboardButton(cancel_button))
    return markup

def gen_inline_markup(options: list[str]) -> InlineKeyboardMarkup:
    """Inline-кнопки (для списка проектов)."""
    markup = InlineKeyboardMarkup(row_width=1)
    for o in options:
        markup.add(InlineKeyboardButton(o, callback_data=o))
    return markup

# Для обновления конкретного поля
attributes = {
    'Имя проекта':    ("Введите новое имя проекта:",   "project_name"),
    'Описание':       ("Введите новое описание:",      "description"),
    'Ссылка':         ("Введите новую ссылку:",         "url"),
    'Статус':         ("Выберите новый статус:",        "status_id"),
}

# ========== Вывод информации о проекте ==========
def info_project(message, user_id: int, project_name: str):
    rec = manager.get_project_info(user_id, project_name)
    if not rec:
        bot.send_message(message.chat.id, "❌ Проект не найден.")
        return
    name, desc, url, status = rec[0]
    skills = manager.get_project_skills(project_name) or "—"
    photo = manager.get_project_photo(project_name, user_id)

    text = (
        f"📁 <b>{name}</b>\n"
        f"📝 Описание: {desc or '—'}\n"
        f"🔗 Ссылка: {url or '—'}\n"
        f"📊 Статус: {status}\n"
        f"🛠️ Навыки: {skills}"
    )
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=hide_board
    )

    if photo:
        with open(f"project_photos/{photo}", "rb") as f:
            bot.send_photo(message.chat.id, f)

# ========== Хэндлеры команд ==========

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Запуск — приветствие и подсказка."""
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот‑портфолио 🤖\n"
        "Сохраняй и просматривай свои проекты!"
    )
    info_handler(message)

@bot.message_handler(commands=['info'])
def info_handler(message):
    """Справка по всем командам."""
    bot.send_message(
        message.chat.id,
        "📌 <b>Доступные команды:</b>\n\n"
        "/new_project – создать новый проект 🆕\n"
        "/projects – список проектов 📋\n"
        "/skills – добавить навык 🛠️\n"
        "/update_projects – изменить проект ✏️\n"
        "/delete – удалить проект ❌\n"
        "/add_description – добавить описание 📄\n"
        "/add_photo – прикрепить фото 📷\n"
        "/info – показать эту справку ℹ️",
        parse_mode='HTML'
    )

# ----- /new_project -----
@bot.message_handler(commands=['new_project'])
def new_project_step1(message):
    bot.send_message(message.chat.id, "📌 Введите название проекта:")
    bot.register_next_step_handler(message, new_project_step2)

def new_project_step2(message):
    name = message.text.strip()
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "🔗 Введите ссылку на проект:")
    bot.register_next_step_handler(message, new_project_step3, user_id, name)

def new_project_step3(message, user_id, name):
    url = message.text.strip()
    statuses = [s[0] for s in manager.get_statuses()]
    bot.send_message(
        message.chat.id,
        "📊 Выберите текущий статус проекта:",
        reply_markup=gen_reply_markup(statuses)
    )
    bot.register_next_step_handler(
        message, new_project_step4, user_id, name, url, statuses
    )

def new_project_step4(message, user_id, name, url, statuses):
    choice = message.text
    if choice == cancel_button:
        return cancel(message)
    if choice not in statuses:
        bot.send_message(
            message.chat.id, "⚠️ Статус не распознан, выберите из списка:",
            reply_markup=gen_reply_markup(statuses)
        )
        return bot.register_next_step_handler(
            message, new_project_step4, user_id, name, url, statuses
        )
    status_id = manager.get_status_id(choice)
    manager.insert_project([(user_id, name, url, status_id)])
    bot.send_message(
        message.chat.id,
        "✅ Проект сохранён!",
        reply_markup=hide_board
    )

# ----- /projects -----
@bot.message_handler(commands=['projects'])
def projects_handler(message):
    user_id = message.from_user.id
    projs = manager.get_projects(user_id)
    if not projs:
        return no_projects(message)

    names = [p[2] for p in projs]
    text = ""
    for _, _, pname, _, url, _ in projs:
        text += f"📁 <b>{pname}</b>\n🔗 {url or '—'}\n\n"
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=gen_inline_markup(names)
    )

@bot.callback_query_handler(func=lambda call: True)
def project_inline_callback(call):
    info_project(call.message, call.from_user.id, call.data)

# ----- /skills -----
@bot.message_handler(commands=['skills'])
def skills_handler(message):
    user_id = message.from_user.id
    projs = manager.get_projects(user_id)
    if not projs:
        return no_projects(message)

    names = [p[2] for p in projs]
    bot.send_message(
        message.chat.id,
        "🛠️ Выберите проект для добавления навыка:",
        reply_markup=gen_reply_markup(names)
    )
    bot.register_next_step_handler(message, skills_step2, names)

def skills_step2(message, names):
    proj = message.text
    if proj == cancel_button:
        return cancel(message)
    if proj not in names:
        bot.send_message(
            message.chat.id, "❌ Проект не найден, повторите:",
            reply_markup=gen_reply_markup(names)
        )
        return bot.register_next_step_handler(message, skills_step2, names)

    all_skills = [s[1] for s in manager.get_skills()]
    bot.send_message(
        message.chat.id,
        "🔧 Выберите навык:",
        reply_markup=gen_reply_markup(all_skills)
    )
    bot.register_next_step_handler(message, skills_step3, proj, all_skills)

def skills_step3(message, proj, all_skills):
    choice = message.text
    uid = message.from_user.id
    if choice == cancel_button:
        return cancel(message)
    if choice not in all_skills:
        bot.send_message(
            message.chat.id, "❌ Навык не распознан, повторите:",
            reply_markup=gen_reply_markup(all_skills)
        )
        return bot.register_next_step_handler(message, skills_step3, proj, all_skills)

    manager.insert_skill(uid, proj, choice)
    bot.send_message(
        message.chat.id,
        f"✅ Навык «{choice}» добавлен к «{proj}».",
        reply_markup=hide_board
    )

# ----- /delete -----
@bot.message_handler(commands=['delete'])
def delete_handler(message):
    user_id = message.from_user.id
    projs = manager.get_projects(user_id)
    if not projs:
        return no_projects(message)

    names = [p[2] for p in projs]
    bot.send_message(
        message.chat.id,
        "❌ Выберите проект для удаления:",
        reply_markup=gen_reply_markup(names)
    )
    bot.register_next_step_handler(message, delete_step2, names)

def delete_step2(message, names):
    choice = message.text
    uid = message.from_user.id
    if choice == cancel_button:
        return cancel(message)
    if choice not in names:
        bot.send_message(
            message.chat.id, "❌ Неверный выбор, повторите:",
            reply_markup=gen_reply_markup(names)
        )
        return bot.register_next_step_handler(message, delete_step2, names)

    pid = manager.get_project_id(choice, uid)
    manager.delete_project(uid, pid)
    bot.send_message(
        message.chat.id,
        f"✅ Проект «{choice}» удалён.",
        reply_markup=hide_board
    )

# ----- /update_projects -----
@bot.message_handler(commands=['update_projects'])
def upd_handler1(message):
    user_id = message.from_user.id
    projs = manager.get_projects(user_id)
    if not projs:
        return no_projects(message)

    names = [p[2] for p in projs]
    bot.send_message(
        message.chat.id,
        "✏️ Выберите проект для редактирования:",
        reply_markup=gen_reply_markup(names)
    )
    bot.register_next_step_handler(message, upd_handler2, names)

def upd_handler2(message, names):
    proj = message.text
    if proj == cancel_button:
        return cancel(message)
    if proj not in names:
        bot.send_message(
            message.chat.id, "❌ Проект не найден, повторите:",
            reply_markup=gen_reply_markup(names)
        )
        return bot.register_next_step_handler(message, upd_handler2, names)

    opts = list(attributes.keys())
    bot.send_message(
        message.chat.id,
        "Что изменить?",
        reply_markup=gen_reply_markup(opts)
    )
    bot.register_next_step_handler(message, upd_handler3, proj)

def upd_handler3(message, proj):
    choice = message.text
    if choice == cancel_button:
        return cancel(message)
    if choice not in attributes:
        bot.send_message(
            message.chat.id, "❌ Опция не распознана, повторите:",
            reply_markup=gen_reply_markup(list(attributes.keys()))
        )
        return bot.register_next_step_handler(message, upd_handler3, proj)

    prompt, col = attributes[choice]
    markup = None
    if col == "status_id":
        statuses = [s[0] for s in manager.get_statuses()]
        markup = gen_reply_markup(statuses)

    bot.send_message(
        message.chat.id,
        prompt,
        reply_markup=markup or hide_board
    )
    bot.register_next_step_handler(message, upd_handler4, proj, col)

def upd_handler4(message, proj, col):
    val = message.text
    uid = message.from_user.id
    if val == cancel_button:
        return cancel(message)

    # если статус — переводим в id
    if col == "status_id":
        sts = [s[0] for s in manager.get_statuses()]
        if val not in sts:
            bot.send_message(
                message.chat.id,
                "❌ Статус неверен, выберите из списка:",
                reply_markup=gen_reply_markup(sts)
            )
            return bot.register_next_step_handler(message, upd_handler4, proj, col)
        val = manager.get_status_id(val)

    manager.update_projects(col, (val, proj, uid))
    bot.send_message(
        message.chat.id,
        "✅ Обновлено!",
        reply_markup=hide_board
    )

# ----- /add_description -----
@bot.message_handler(commands=['add_description'])
def add_desc1(message):
    uid = message.from_user.id
    projs = manager.get_projects(uid)
    if not projs:
        return no_projects(message)

    names = [p[2] for p in projs]
    bot.send_message(
        message.chat.id,
        "📄 Выберите проект для описания:",
        reply_markup=gen_reply_markup(names)
    )
    bot.register_next_step_handler(message, add_desc2, names)

def add_desc2(message, names):
    proj = message.text
    if proj == cancel_button:
        return cancel(message)
    if proj not in names:
        bot.send_message(
            message.chat.id, "❌ Проект не найден, повторите:",
            reply_markup=gen_reply_markup(names)
        )
        return bot.register_next_step_handler(message, add_desc2, names)

    bot.send_message(
        message.chat.id,
        "📝 Введите текст описания:",
        reply_markup=hide_board
    )
    bot.register_next_step_handler(message, add_desc3, proj)

def add_desc3(message, proj):
    text = message.text
    uid = message.from_user.id
    manager.update_projects("description", (text, proj, uid))
    bot.send_message(
        message.chat.id,
        "✅ Описание сохранено!",
        reply_markup=hide_board
    )

# ----- /add_photo -----
@bot.message_handler(commands=['add_photo'])
def add_photo1(message):
    uid = message.from_user.id
    projs = manager.get_projects(uid)
    if not projs:
        return no_projects(message)

    names = [p[2] for p in projs]
    bot.send_message(
        message.chat.id,
        "📷 Выберите проект для фото:",
        reply_markup=gen_reply_markup(names)
    )
    bot.register_next_step_handler(message, add_photo2, names)

def add_photo2(message, names):
    proj = message.text
    if proj == cancel_button:
        return cancel(message)
    if proj not in names:
        bot.send_message(
            message.chat.id, "❌ Проект не найден, повторите:",
            reply_markup=gen_reply_markup(names)
        )
        return bot.register_next_step_handler(message, add_photo2, names)

    bot.send_message(
        message.chat.id,
        "Отправьте фото проекта в ответ на это сообщение:",
        reply_markup=hide_board
    )
    bot.register_next_step_handler(message, add_photo3, proj)

def add_photo3(message, proj):
    if message.content_type != 'photo':
        bot.send_message(message.chat.id, "❌ Это не фото, попробуйте ещё раз.")
        return bot.register_next_step_handler(message, add_photo3, proj)

    uid = message.from_user.id
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    data = bot.download_file(file_info.file_path)

    filename = f"{uid}_{proj}.jpg"
    path = f"project_photos/{filename}"
    with open(path, 'wb') as f:
        f.write(data)

    manager.update_projects("photo", (filename, proj, uid))
    bot.send_message(
        message.chat.id,
        "✅ Фото сохранено!",
        reply_markup=hide_board
    )

# ----- Ловим всё остальное -----
@bot.message_handler(func=lambda m: True)
def fallback_handler(message):
    uid = message.from_user.id
    names = [p[2] for p in manager.get_projects(uid)]
    if message.text in names:
        return info_project(message, uid, message.text)
    bot.reply_to(message, "Нужна помощь?")
    info_handler(message)

# ========== Старт поллинга ==========
if __name__ == '__main__':
    bot.infinity_polling()
