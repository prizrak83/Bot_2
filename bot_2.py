import telebot as tb
import configparser
import sqlite3
import datetime


HELP_TEXT = 'User help'

ADMIN_HELP_TEXT = '/showguests - показать список гостей\n' \
                  '/showusers - показать список пользователей\n' \
                  '/clearguests - очистить список гостей\n' \
                  '/remove <ID> - удалить пользователя\n' \
                  '/rename <ID>:<новое имя> - переименовать пользователя\n' \
                  '/adduser <ID>:<имя пользователя> - добавить полльзователя\n' \
                  '/acl <ID>:<цифра от 0 до 3>  изменить права пользователя где 0 - администратор 3 - гость'


config = configparser.ConfigParser()
config.read('config.ini')
token_file = config.get('Settings', 'token_file')
proxy_type = config.get('Settings', 'proxy_type')
proxy_address = config.get('Settings', 'proxy_address')


f = open(token_file)
bot = tb.TeleBot(f.read())
f.close()

tb.apihelper.proxy = {proxy_type: proxy_address}

# conn = sqlite3.connect("database.db")
# cursor = conn.cursor()


# cursor.execute("""CREATE TABLE users(id integer, name text, rights integer)
#               """)
# cursor.execute("""CREATE TABLE guests(id integer, last_connect text)
#               """)
# cursor.execute("drop table guests")
# entities =(  ,  )
# cursor.execute("""INSERT INTO users(id, name, rights) VALUES(?, ?,?)""", entities)
# conn.commit()
# cursor.close()


def acl_check(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT rights FROM users WHERE id =:id', {'id': user_id})
    right_num = cursor.fetchone()
    if right_num is None:
        cursor.close()
        return 3
    else:
        cursor.close()
        return right_num[0]


def add_guest_id(guest_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute('SELECT id FROM guests WHERE id =:id', {'id': guest_id})
    guest_present = cursor.fetchone()
    if guest_present is None:
        entities = (guest_id, now.isoformat())
        cursor.execute("""INSERT INTO guests(id, last_connect) VALUES(?, ?) """, entities)
    else:
        cursor.execute('UPDATE guests SET last_connect =:last_connect WHERE id =:id ',
                       {'last_connect': now.isoformat(), 'id': guest_id})
    conn.commit()
    cursor.close()


def del_guest(guest_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM guests WHERE id =:id', {'id': guest_id})
    guest_present = cursor.fetchone()
    if guest_present is None:
        return
    else:
        cursor.execute('DELETE FROM guests WHERE id =:id', {'id': guest_id})
    conn.commit()
    cursor.close()


def del_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE id =:id', {'id': user_id})
    user_present = cursor.fetchone()
    if user_present is None:
        return False
    else:
        cursor.execute('DELETE FROM users WHERE id =:id', {'id': user_id})
    conn.commit()
    cursor.close()
    return True


def rename_user(user_id, new_name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE id =:id', {'id': user_id})
    user_present = cursor.fetchone()
    if user_present is None:
        cursor.close()
        return False
    else:
        cursor.execute('UPDATE users SET name =:name WHERE id =:id', {'name': new_name, 'id': user_id})
        conn.commit()
        cursor.close()
        return True


def user_add(user_id, name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE id =:id', {'id': user_id})
    user_present = cursor.fetchone()
    if user_present is None:
        entities = (user_id, name, 1)
        cursor.execute("""INSERT INTO users(id, name, rights) VALUES(?, ?, ?) """, entities)
    conn.commit()
    cursor.close()


def remove_all_guests():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("drop table guests")
    cursor.execute("""CREATE TABLE guests(id integer, last_connect text)""")
    conn.commit()
    cursor.close()


def set_acl(user_id, acl):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE id =:id', {'id': user_id})
    user_present = cursor.fetchone()
    if user_present is None:
        cursor.close()
        return False
    else:
        cursor.execute('UPDATE users SET rights =:rights WHERE id =:id', {'rights': acl, 'id': user_id})
        conn.commit()
        cursor.close()
        return True


@bot.message_handler(commands=['acl'])
def change_access(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    index = message.text.find(':')
    if len(message.text) == 4:
        bot.send_message(message.chat.id, 'Неуказан id')
        return
    elif index == -1:
        bot.send_message(message.chat.id, 'Направильный формат команды')
        return
    id_user = int(message.text[5:index])
    print(id_user)
    if message.chat.id == id_user:
        bot.send_message(message.chat.id, 'Нельзя изменить свой уровень доступа')
        return
    new_acl = int(message.text[index+1])
    if set_acl(id_user, new_acl):
        bot.send_message(message.chat.id, 'Уровень доступа изменён')
        show_users(message)
    else:
        bot.send_message(message.chat.id, 'Пользователь не найден')


@bot.message_handler(commands=['clearguests'])
def clearguests(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    remove_all_guests()
    bot.send_message(message.chat.id, 'Список гостей очищен')


@bot.message_handler(commands=['remove'])
def remove(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    if len(message.text) == 7:
        bot.send_message(message.chat.id, 'Неуказан id')
        return
    id_user = int(message.text[7:])
    if message.chat.id == id_user:
        bot.send_message(message.chat.id, 'Нельзя удалить себя')
        return
    if del_user(id_user):
        show_users(message)
    else:
        bot.send_message(message.chat.id, 'Пользователь не найден')


@bot.message_handler(commands=['rename'])
def rename(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    index = message.text.find(':')
    if len(message.text) == 7:
        bot.send_message(message.chat.id, 'Неуказан id')
        return
    elif index == -1:
        bot.send_message(message.chat.id, 'Направильный формат команды')
        return
    id_user = int(message.text[8:index])
    name_user = message.text[index+1:]
    if rename_user(id_user, name_user):
        bot.send_message(message.chat.id, 'Пользователь перименован')
        show_users(message)
    else:
        bot.send_message(message.chat.id, 'Пользователь не найден')


@bot.message_handler(commands=['adduser'])
def add_user(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    index = message.text.find(':')
    if len(message.text) == 8:
        bot.send_message(message.chat.id, 'Неуказан id')
        return
    elif index == -1:
        bot.send_message(message.chat.id, 'Направильный формат команды')
        return
    id_user = int(message.text[9:index])
    name_user = message.text[index+1:]
    del_guest(id_user)
    user_add(id_user, name_user)
    show_users(message)


@bot.message_handler(commands=['showguests'])
def show_guests(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM guests')
    guest_list = cursor.fetchall()
    text = 'Список гостей'
    for guest in guest_list:
        text = text+'\n'+str(guest[0])+' '+guest[1]
    bot.send_message(message.chat.id, text)
    cursor.close()


@bot.message_handler(commands=['showusers'])
def show_users(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users_list = cursor.fetchall()
    text = 'Список зарегестрированных пользователей'
    for user in users_list:
        text = text+'\n'+str(user[0])+' '+user[1]+' Уровень доступа '+str(user[2])
    bot.send_message(message.chat.id, text)
    cursor.close()


@bot.message_handler(commands=['start', 'help'])
def start_message(message):
    print(message.chat.id)
    acl = acl_check(message.chat.id)
    if acl > 2:
        add_guest_id(message.chat.id)
        bot.send_message(message.chat.id, 'Ошибка доступа')
        return
    bot.send_message(message.chat.id, HELP_TEXT)
    if acl < 1:
        bot.send_message(message.chat.id, ADMIN_HELP_TEXT)


bot.polling(none_stop=True, timeout=123)
