import json
import os
import telebot

# ---------- Конфигурация ----------
TOKEN = os.getenv("BOT_TOKEN")
JSON_FILE = "klubklubromance.json"
ACHIEVEMENTS_FILE = "achievements.json"

bot = telebot.TeleBot(TOKEN)

# ---------- Загрузка сюжета ----------
def resolve_ref(ref, root):
    if not ref.startswith("#/"):
        return None
    parts = ref[2:].split('/')
    current = root
    for part in parts:
        if part.isdigit():
            current = current[int(part)]
        else:
            current = current[part]
    return current

def collect_nodes(obj, nodes_dict):
    if isinstance(obj, dict):
        if 'id' in obj:
            node_id = obj['id']
            if node_id not in nodes_dict:
                nodes_dict[node_id] = obj.copy()
        for key, value in obj.items():
            if key == '$ref':
                continue
            collect_nodes(value, nodes_dict)
    elif isinstance(obj, list):
        for item in obj:
            collect_nodes(item, nodes_dict)

def build_nodes_with_resolved_refs(root):
    raw_nodes = {}
    collect_nodes(root, raw_nodes)
    nodes = {}
    for node_id, node_data in raw_nodes.items():
        text = node_data.get('text', '')
        edges = []
        for edge in node_data.get('edges', []):
            color = edge.get('color', {})
            r, g = color.get('r', 0), color.get('g', 0)
            if g > 0.8 and r < 0.5:
                choice_type = 'positive'
            elif r > 0.9 and g < 0.5:
                choice_type = 'negative'
            else:
                choice_type = 'neutral'
            edge_text = edge.get('text', '')
            to_obj = edge.get('to')
            if to_obj is None:
                to_id = None
            elif isinstance(to_obj, dict):
                if 'id' in to_obj:
                    to_id = to_obj['id']
                elif '$ref' in to_obj:
                    target = resolve_ref(to_obj['$ref'], root)
                    to_id = target['id'] if target and 'id' in target else None
                else:
                    to_id = None
            else:
                to_id = None
            edges.append({'text': edge_text, 'to_id': to_id, 'type': choice_type})
        nodes[node_id] = {'text': text, 'edges': edges}
    return nodes

def load_game_data(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return build_nodes_with_resolved_refs(data)

try:
    nodes = load_game_data(JSON_FILE)
    START_NODE = "2:2"
    print(f"Сюжет загружен. Узлов: {len(nodes)}")
except Exception as e:
    print(f"Ошибка загрузки: {e}")
    exit()

# ---------- Замена стартового текста ----------
CUSTOM_START_TEXT = """Прекрасный весенний вечер, солнце красиво заходит.

Вы — студент 2 курса НИУ ВШЭ. Только что кончилась самая душная пара на свете, посвященная антропологическому исследованию карликов. Вы измотаны, но душа жаждет приключений. Поэтому вы решаете заглянуть в самое приключенческое место на свете (Китай-городе): Клуб под названием «Клуб». Вы отправляетесь, зная, что у вас есть кес рублей, сигарета, медиатор и плёночный фотик.

Вы на месте. Пролезая через толпу нефоров, Вы оказываетесь в подвале. Странный запах. Около сцены сидят немытые и слегка волосатые панки, играют хиты нулевых и десятых годов.

Вы почти сразу жалеете, что попали сюда, но замечаете у бара шикарную блондинку в черных очках и лабубой на сумочке, пьющей ягодный джин и подпевающей во все горло песне Рианны. Вы узнаете в ней админку нишевого телеграм-канала Алису.

При этом вас пронзает божественный свет, исходящий из Книжного в Клубе. Там вы видите немного кудрявого фембоя с грустными глазами, просматривающего книги. У него бас-гитара за спиной и футболка со Скоттом Пилигримом. Его песни попадались вам в Моей волне в Яндекс Музыке. Кажется, его зовут Ваня.

Вы понимаете, что чтобы не сойти с ума, вам нужно подойти к одному из этих хайповых людей или в ужасе сбежать. Что вы сделаете? Выбирая Ваню, вы признаете, что вы женщина. В случае с Алисой — не принципиально.

P.S. употребление алкоголя и табачной продукции вредит вашему здоровью. Игра 18+"""

nodes[START_NODE]["text"] = CUSTOM_START_TEXT

# ---------- Утилиты ----------
def replace_name(text, name):
    return text.replace("<Имя>", f"Меня зовут {name}.").replace("<имя>", f"Меня зовут {name}.")

# ---------- Система достижений ----------
def load_achievements():
    if os.path.exists(ACHIEVEMENTS_FILE):
        with open(ACHIEVEMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_achievements(data):
    with open(ACHIEVEMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_achievements()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "completed_endings": [],
            "achievements": [],
            "username": "",
            "first_name": ""
        }
    return data, uid

def update_user_info(user_id, username, first_name):
    """Обновляет информацию о пользователе в achievements."""
    data, uid = get_user_data(user_id)
    data[uid]["username"] = username
    data[uid]["first_name"] = first_name
    save_achievements(data)

def add_ending(user_id, ending_id):
    data, uid = get_user_data(user_id)
    if ending_id not in data[uid]["completed_endings"]:
        data[uid]["completed_endings"].append(ending_id)
        save_achievements(data)
        return True
    return False

def check_achievements(user_id):
    data, uid = get_user_data(user_id)
    user = data[uid]
    completed = user["completed_endings"]
    count = len(completed)
    earned = user["achievements"]
    new = []

    secret_map = {
        "secret_seva": "Скрытая концовка: Сева",
        "secret_anya": "Скрытая концовка: Аня",
        "secret_marisa": "Скрытая концовка: Мариса",
        "secret_darina": "Скрытая концовка: Дарина"
    }
    for eid, name in secret_map.items():
        if eid in completed and name not in earned:
            new.append(name)
            earned.append(name)

    if count >= 1 and "Первая кровь" not in earned:
        new.append("Первая кровь")
        earned.append("Первая кровь")
    if count >= 5 and "Опытный игрок (5)" not in earned:
        new.append("Опытный игрок (5)")
        earned.append("Опытный игрок (5)")
    if count >= 10 and "Профессионал (10)" not in earned:
        new.append("Профессионал (10)")
        earned.append("Профессионал (10)")
    if count >= 64 and "Задрот (все концовки)" not in earned:
        new.append("Задрот (все концовки)")
        earned.append("Задрот (все концовки)")

    if new:
        save_achievements(data)
    return new

def get_detailed_stats(user_id):
    data, uid = get_user_data(user_id)
    endings = data[uid]["completed_endings"]
    achievements = data[uid]["achievements"]
    total = len(endings)
    alice_wins = sum(1 for e in endings if e == "alice_pos")
    alice_losses = sum(1 for e in endings if e == "alice_neg")
    vanya_wins = sum(1 for e in endings if e == "vanya_pos")
    vanya_losses = sum(1 for e in endings if e == "vanya_neg")
    secret = sum(1 for e in endings if e.startswith("secret_"))
    return {
        "total": total,
        "alice_wins": alice_wins,
        "alice_losses": alice_losses,
        "vanya_wins": vanya_wins,
        "vanya_losses": vanya_losses,
        "secret": secret,
        "achievements": achievements
    }

# ---------- Глобальные концовки ----------
def get_global_ending(character, pos_count):
    if character == 'alice':
        if pos_count >= 3:
            return ("Алиса довольна сегодняшним вечером. Вы знакомитесь с фриками и студентами МГУ, "
                    "пьете дешевый алкоголь, смеетесь, тусите с Ваней, которого вы не выбрали в начале, "
                    "и обмениваетесь телеграмами. На утро она присылает вам похмельный кружочек. "
                    "Возможно вас ждет ситьюэйшеншип.")
        else:
            return ("Алиса говорит вам, что у нее завтра дедлайн на майноре по антропологии, "
                    "поэтому ей нужно ехать домой. В тот же вечер она напишет в канале про свою кринжовую "
                    "интеракцию с подписчиком и выложит пьяный кружочк с Ваней, которого вы не выбрали.")
    elif character == 'vanya':
        if pos_count >= 3:
            return ("Вы получили её, потому что вам удалось получить контакт Ванёчка каким-то из всех возможных путей. "
                    "Вы общались мило, и довольно долго. В какой-то момент вы вновь встретились, потому что Ванечка увидел "
                    "в вас светлую душу альтушки. Ну или просто крутой девочки! Так проходят месяца. Оказывается, что вас "
                    "и вправду связывает много общего. Становится ясно, что эти забавные приключения в Клубе «Клуб» смогли "
                    "привести вас к нечто большему, чем просто угарные приключения после пар по антропологии карликов.")
        else:
            return ("Все очень плохо. У Вани не осталось о вас крутых впечатлений, поэтому он, грустный "
                    "(как и всегда после концерта) решил уехать домой в Жуковский один. Спустя года он о вас и не вспомнит.")
    else:
        return "Персонаж не определён."

# ---------- Секретные концовки ----------
def check_secret_name(name):
    name_lower = name.lower().strip()
    secrets = {
        "сева": ("secret_seva", "Ох, вы выбрали страшный путь, Всеволод. Вы сами знаете, что произойдет сегодня, так что в этой игре не было предусмотрено приключение в Клуб Клуб. Вы едете к вам на хату в Сколково, где происходят загадочные вещи, о которых лучше не рассказывать. Сходящий с ума пылесос подглядывает за тем, что происходит в спальне. Ужас. Напишите Ваньку в тг."),
        "аня": ("secret_anya", "Поздравляю, у вас выпала секретная концовка, хотя игра не успела начаться. Анна, ох, прекрасное имя ваше, лик ваш прекрасный... Тут даже говорить нечего. Вы хватаете Ванька, он хватает вас. Угарчик. Короче, я не буду расписывать фанфики. Чтобы узнать другие концовки, можете выбрать другое имя."),
        "анна": ("secret_anya", "Поздравляю, у вас выпала секретная концовка, хотя игра не успела начаться. Анна, ох, прекрасное имя ваше, лик ваш прекрасный... Тут даже говорить нечего. Вы хватаете Ванька, он хватает вас. Угарчик. Короче, я не буду расписывать фанфики. Чтобы узнать другие концовки, можете выбрать другое имя."),
        "мариса": ("secret_marisa", "Поздравляю, у вас выпала секретная концовка, хотя игра не успела начаться. Ох, Мариса, красотка. Ваня давным давно ожидал вашего пришествия в Клуб Клуб. Происходят страшные вещи, о которых лучше не писать. Все хорошо, и все счастливы, вот и конец. Если хотите узнать, что произошло, напишите Ване в телеграме. Чтобы узнать другие концовки, можете выбрать другое имя."),
        "marisa": ("secret_marisa", "Поздравляю, у вас выпала секретная концовка, хотя игра не успела начаться. Ох, Мариса, красотка. Ваня давным давно ожидал вашего пришествия в Клуб Клуб. Происходят страшные вещи, о которых лучше не писать. Все хорошо, и все счастливы, вот и конец. Если хотите узнать, что произошло, напишите Ване в телеграме. Чтобы узнать другие концовки, можете выбрать другое имя."),
        "дарина": ("secret_darina", "Поздравляю, у вас выпала секретная концовка, хотя игра не успела начаться. Ванек хотел оставить вам секретное послание. Очень жаль, что мы больше не общаемся. «...». Чтобы узнать другие концовки, можете выбрать другое имя."),
        "ancimo": ("secret_darina", "Поздравляю, у вас выпала секретная концовка, хотя игра не успела начаться. Ванек хотел оставить вам секретное послание. Очень жаль, что мы больше не общаемся. «...». Чтобы узнать другие концовки, можете выбрать другое имя.")
    }
    return secrets.get(name_lower, (None, None))

# ---------- Хранилище сессий ----------
user_sessions = {}

def init_session(chat_id, name, username, first_name):
    user_sessions[chat_id] = {
        'current_id': START_NODE,
        'history': [],
        'pos_count': 0,
        'neg_count': 0,
        'character': None,
        'inventory': {'money': 1000, 'cigarette': True, 'mediator': True, 'camera': True},
        'player_name': name,
        'tg_username': username,
        'tg_first_name': first_name,
        'current_edges': {},
        'visited': set()
    }

def clear_session(chat_id):
    if chat_id in user_sessions:
        del user_sessions[chat_id]

def handle_inventory(chat_id, edge_text):
    session = user_sessions.get(chat_id)
    if not session:
        return True
    inv = session['inventory']
    text_lower = edge_text.lower()

    if 'сигарет' in text_lower and inv['cigarette']:
        inv['cigarette'] = False
        bot.send_message(chat_id, "(🚬 Вы использовали последнюю сигарету)")
    if 'медиатор' in text_lower and inv['mediator']:
        inv['mediator'] = False
        bot.send_message(chat_id, "(⚡ Вы отдали медиатор)")
    if ('фот' in text_lower or 'пленк' in text_lower) and inv['camera']:
        inv['camera'] = False
        bot.send_message(chat_id, "(📷 Вы использовали плёнку)")

    if session['current_id'] in ["12:340", "39:1312"]:
        buy_keywords = ['угостить', 'давай', 'пиво', 'ерш', 'коктейль', 'сет']
        if any(kw in text_lower for kw in buy_keywords):
            if inv['money'] < 1300:
                needed = 1300 - inv['money']
                inv['money'] = 0
                bot.send_message(chat_id, f"💰 Вы украли у рядом лежащего нефора его последние {needed} рублей и расплатились. Совесть нечиста, но сюжет продолжается!")
            else:
                inv['money'] -= 1300
                bot.send_message(chat_id, f"💰 Вы потратили 1300 руб. Осталось: {inv['money']} руб.")
    return True

# ---------- Главное меню ----------
def main_menu(chat_id):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn1 = telebot.types.InlineKeyboardButton("🎮 Новая игра", callback_data="new_game")
    btn2 = telebot.types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    btn3 = telebot.types.InlineKeyboardButton("🏆 Достижения", callback_data="achievements")
    btn4 = telebot.types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    btn5 = telebot.types.InlineKeyboardButton("💸 Донат на развитие", url="https://tips.yandex.ru/guest/payment/7139760")
    btn6 = telebot.types.InlineKeyboardButton("📋 Лидеры", callback_data="leaderboard")
    markup.add(btn1, btn2, btn3, btn4)
    markup.add(btn5, btn6)
    bot.send_message(chat_id, "🏠 **Главное меню**\nВыберите действие:", parse_mode="Markdown", reply_markup=markup)

# ---------- Лидерборд ----------
@bot.message_handler(commands=['leaderboard'])
def leaderboard_cmd(message):
    data = load_achievements()
    users = []
    for uid, info in data.items():
        count = len(info.get("completed_endings", []))
        if count > 0:
            username = info.get("username", "")
            first_name = info.get("first_name", "")
            users.append((uid, count, username, first_name))
    users.sort(key=lambda x: x[1], reverse=True)
    top = users[:10]
    if not top:
        bot.send_message(message.chat.id, "Пока нет игроков в таблице лидеров.")
        return
    text = "🏆 **Топ игроков по количеству пройденных концовок** 🏆\n\n"
    for i, (uid, count, username, first_name) in enumerate(top, 1):
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
        else:
            display_name = f"ID {uid}"
        text += f"{i}. {display_name} — {count}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ---------- Отправка узла ----------
def send_node(chat_id):
    session = user_sessions.get(chat_id)
    if not session:
        main_menu(chat_id)
        return

    current_id = session['current_id']
    node = nodes.get(current_id)
    if not node:
        bot.send_message(chat_id, "Ошибка: узел не найден. Возвращаю в меню.")
        clear_session(chat_id)
        main_menu(chat_id)
        return

    if current_id in session['visited']:
        bot.send_message(chat_id, "Обнаружен цикл! Игра прервана.")
        clear_session(chat_id)
        main_menu(chat_id)
        return
    session['visited'].add(current_id)

    normal = [e for e in node['edges'] if 'connector line' not in e['text'].lower()]
    connector = [e for e in node['edges'] if 'connector line' in e['text'].lower()]

    text = replace_name(node['text'], session['player_name'])

    if normal:
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
        for e in normal:
            btn = replace_name(e['text'], session['player_name'])
            markup.add(telebot.types.KeyboardButton(btn))
        markup.add(telebot.types.KeyboardButton("🏠 В меню"))
        edge_map = {replace_name(e['text'], session['player_name']): e for e in normal}
        session['current_edges'] = edge_map
        bot.send_message(chat_id, text, reply_markup=markup)

    elif connector:
        bot.send_message(chat_id, text)
        session['current_id'] = connector[0]['to_id']
        send_node(chat_id)

    else:
        # Конец игры
        bot.send_message(chat_id, text, reply_markup=telebot.types.ReplyKeyboardRemove())

        # ID концовки
        if session['character'] == 'alice':
            ending_id = "alice_pos" if session['pos_count'] >= 3 else "alice_neg"
        elif session['character'] == 'vanya':
            ending_id = "vanya_pos" if session['pos_count'] >= 3 else "vanya_neg"
        else:
            ending_id = "unknown"

        # Сохраняем информацию о пользователе для лидерборда
        update_user_info(chat_id, session.get('tg_username', ''), session.get('tg_first_name', ''))

        # Достижения
        if add_ending(chat_id, ending_id):
            new_achs = check_achievements(chat_id)
            if new_achs:
                bot.send_message(chat_id, "🏆 Новые достижения:\n" + "\n".join(f"• {a}" for a in new_achs))

        # Глобальная концовка
        global_ending = get_global_ending(session['character'], session['pos_count'])
        bot.send_message(chat_id, global_ending)

        # Краткая сводка
        summary = f"📋 **Сводка игры**\n"
        summary += f"Персонаж: {'Алиса' if session['character']=='alice' else 'Ваня'}\n"
        summary += f"Позитивных выборов: {session['pos_count']}\n"
        summary += f"Негативных выборов: {session['neg_count']}\n"
        bot.send_message(chat_id, summary, parse_mode="Markdown")

        clear_session(chat_id)
        main_menu(chat_id)

# ---------- Обработчики команд ----------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    clear_session(chat_id)
    main_menu(chat_id)

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    chat_id = message.chat.id
    clear_session(chat_id)
    main_menu(chat_id)

@bot.message_handler(commands=['achievements'])
def achievements_cmd(message):
    chat_id = message.chat.id
    stats = get_detailed_stats(chat_id)
    text = f"📊 **Ваша статистика**\n"
    text += f"Всего игр: {stats['total']}\n"
    text += f"Алиса: побед {stats['alice_wins']}, поражений {stats['alice_losses']}\n"
    text += f"Ваня: побед {stats['vanya_wins']}, поражений {stats['vanya_losses']}\n"
    text += f"Секретных концовок: {stats['secret']}\n\n"
    if stats['achievements']:
        text += "🏅 **Достижения:**\n" + "\n".join(f"• {a}" for a in stats['achievements'])
    else:
        text += "Пока нет достижений. Играйте!"
    bot.send_message(chat_id, text, parse_mode="Markdown")

# ---------- Админская команда ----------
ADMIN_IDS = [411500197, 513528979]  # замените на свой ID

def get_admin_stats():
    data = load_achievements()
    total_users = len(data)
    total_endings = sum(len(u["completed_endings"]) for u in data.values())
    endings_count = {}
    for u in data.values():
        for e in u["completed_endings"]:
            endings_count[e] = endings_count.get(e, 0) + 1
    return total_users, total_endings, endings_count

@bot.message_handler(commands=['admin_stats'])
def admin_stats_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "У вас нет прав для этой команды.")
        return
    total_users, total_endings, endings_count = get_admin_stats()
    text = f"👥 Всего игроков: {total_users}\n"
    text += f"🎮 Всего сыграно концовок: {total_endings}\n\n"
    text += "📊 Статистика по концовкам:\n"
    for e, cnt in sorted(endings_count.items(), key=lambda x: -x[1]):
        text += f"{e}: {cnt}\n"
    bot.send_message(message.chat.id, text)

# ---------- Обработчик инлайн-кнопок ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "new_game":
        bot.answer_callback_query(call.id)
        bot.edit_message_text("Введите ваше имя:", chat_id, message_id)
        user_sessions[chat_id] = {'waiting_name': True}

    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        stats = get_detailed_stats(chat_id)
        text = f"📊 **Ваша статистика**\n"
        text += f"Всего игр: {stats['total']}\n"
        text += f"Алиса: побед {stats['alice_wins']}, поражений {stats['alice_losses']}\n"
        text += f"Ваня: побед {stats['vanya_wins']}, поражений {stats['vanya_losses']}\n"
        text += f"Секретных концовок: {stats['secret']}"
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
        bot.send_message(chat_id, "Вернуться в меню:", reply_markup=markup)

    elif call.data == "achievements":
        bot.answer_callback_query(call.id)
        stats = get_detailed_stats(chat_id)
        if stats['achievements']:
            text = "🏅 **Ваши достижения:**\n" + "\n".join(f"• {a}" for a in stats['achievements'])
        else:
            text = "У вас пока нет достижений. Играйте и открывайте их!"
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
        bot.send_message(chat_id, "Вернуться в меню:", reply_markup=markup)

    elif call.data == "leaderboard":
    bot.answer_callback_query(call.id)
    # Загружаем статистику
    data = load_achievements()
    users = []
    for uid, info in data.items():
        count = len(info.get("completed_endings", []))
        if count > 0:
            username = info.get("username", "")
            first_name = info.get("first_name", "")
            users.append((uid, count, username, first_name))
    users.sort(key=lambda x: x[1], reverse=True)
    top = users[:10]
    if not top:
        bot.send_message(chat_id, "Пока нет игроков в таблице лидеров.")
        return
    text = "🏆 **Топ игроков по количеству пройденных концовок** 🏆\n\n"
    for i, (uid, count, username, first_name) in enumerate(top, 1):
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
        else:
            display_name = f"ID {uid}"
        text += f"{i}. {display_name} — {count}\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

    elif call.data == "help":
        bot.answer_callback_query(call.id)
        help_text = """
❓ **Помощь по игре**

Вы — студент ВШЭ, попавший в клуб «Клуб». Ваша цель — завести знакомство с Алисой или Ваней и получить одну из множества концовок.

- В начале введите имя (от него зависят секретные концовки).
- Делайте выборы, нажимая на кнопки.
- Можно в любой момент прервать игру и вернуться в меню кнопкой «🏠 В меню».
- После окончания игры результат сохраняется в статистику, а достижения открываются.

Команды:
/start — главное меню
/menu — вернуться в меню (во время игры)
/achievements — посмотреть достижения и статистику
/leaderboard — топ игроков по числу концовок

ЕБАШИМ
"""
        bot.edit_message_text(help_text, chat_id, message_id, parse_mode="Markdown")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
        bot.send_message(chat_id, "Вернуться в меню:", reply_markup=markup)

    elif call.data == "back_to_menu":
        bot.answer_callback_query(call.id)
        bot.delete_message(chat_id, message_id)
        main_menu(chat_id)

# ---------- Обработчик текстовых сообщений ----------
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_sessions:
        bot.send_message(chat_id, "Напишите /start для начала игры.")
        return

    session = user_sessions[chat_id]

    if session.get('waiting_name'):
        name = text
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        init_session(chat_id, name, username, first_name)
        bot.send_message(chat_id, f"Приятно познакомиться, {name}! Начинаем...")
        send_node(chat_id)
        return

    if text == "🏠 В меню":
        clear_session(chat_id)
        main_menu(chat_id)
        return

    current_edges = session.get('current_edges', {})
    if text not in current_edges:
        bot.send_message(chat_id, "Пожалуйста, выберите вариант из меню (кнопки внизу) или нажмите «🏠 В меню».")
        return

    edge = current_edges[text]

    if session['character'] is None:
        if 'Алис' in text:
            session['character'] = 'alice'
        elif 'Ван' in text:
            session['character'] = 'vanya'
            secret_id, secret_text = check_secret_name(session['player_name'])
            if secret_id:
                bot.send_message(chat_id, secret_text, reply_markup=telebot.types.ReplyKeyboardRemove())
                add_ending(chat_id, secret_id)
                new_achs = check_achievements(chat_id)
                if new_achs:
                    bot.send_message(chat_id, "🏆 Новые достижения:\n" + "\n".join(f"• {a}" for a in new_achs))
                clear_session(chat_id)
                main_menu(chat_id)
                return

    handle_inventory(chat_id, edge['text'])

    if edge['type'] == 'positive':
        session['pos_count'] += 1
    elif edge['type'] == 'negative':
        session['neg_count'] += 1

    session['history'].append(f"{session['current_id']}: {edge['text']}")

    session['current_id'] = edge['to_id']
    session.pop('current_edges', None)
    send_node(chat_id)

# ---------- Запуск ----------
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()




