import telebot as tb
import configparser
import sqlite3
import datetime
from time import sleep, time
from multiprocessing import Process

HELP_TEXT = '/find <название> - поиск пароля по названию, команда без атрибута выдаёт все записи из таблицы\n' \
       '/show <номер записи> - показ полной информации по номеру\n' \
       'Сообщения с паролями удаляется через 5 минут\n' \
       '/addpswd <форматированная строка для добавления данных в базу>- добпвление новой записи в БД\n' \
       'формат строки - <разделитель>название<разделитель>текущий логин/пароль<разделитель>[комментарий] <разделитель>' \
       'старые пароли\n' \
       'в качестве разделителя может быть любой символ которого нет в логине пароле и коммантари\n' \
       '/changepswd <форматированная строка для изменения данных> - обновление пароля и комментария в БД\n' \
       'формат строки - <разделитель>номер строки<разделитель> новый логин/пароль<разделитель>[комментарий]'

ADMIN_HELP_TEXT = 'Администрирование БД\n' \
                  '/delete_pswd <номер записи> - удаляет строку из БД\n' \
                  '/change_data <форматированная строка>\n' \
                  'формат строки - <разделитель>номер записи<разделитель>название<разделитель>текущий логин/пароль' \
                  '<разделитель>[комментарий]<разделитель>старые пароли\n' \
                  '/history_pswd <номер записи> - вывод истории изменений данной строки' \
                  '(история сохраняется только для команды /changepswd)\n' \
                  'Команды управления пользователями\n' \
                  '/showguests - показать список гостей\n' \
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
config.read('proxy.ini')
proxy_address = config.get('Settings', 'proxy_address')
first_start = True

f = open(token_file)
bot = tb.TeleBot(f.read())
f.close()

tb.apihelper.proxy = {proxy_type: proxy_address}


def new_data(data_name, current_data, comment, old_data):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    entities = (data_name, current_data, comment, old_data)
    cursor.execute('SELECT * FROM main_table WHERE data_name =:data_name', {'data_name': data_name})
    data_present = cursor.fetchone()
    if not(data_present is None):
        cursor.close()
        return False
    else:
        cursor.execute("""INSERT INTO main_table(data_name, current_data, comment, old_data) 
                      VALUES(?, ?, ?, ?)""", entities)
    conn.commit()
    cursor.close()
    return True


def change_data(data_id, new_data, comment, user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM main_table WHERE data_id =:data_id', {'data_id': data_id})
    data_present = cursor.fetchone()
    if data_present is None:
        cursor.close()
        return False
    else:
        if comment == '':
            comment = data_present[3]
        old_data = data_present[2] + ' ' + data_present[4]
        now = datetime.datetime.now()
        entities = (user_id, now.isoformat(), data_present[2], new_data, data_present[0])
        cursor.execute('INSERT INTO change_log(user_id, date_log, old_data, new_data, main_table_id)'
                       ' VALUES(?, ?, ?, ?, ?)', entities)
        cursor.execute("""UPDATE main_table SET  current_data =:current_data , comment =:comment 
                      , old_data =:old_data WHERE  data_id =:data_id 
                     """, {'data_id': data_id, 'current_data': new_data, 'old_data': old_data, 'comment': comment})
        conn.commit()
        cursor.close()


def find_data(data_name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT data_id, data_name, current_data
                    FROM main_table WHERE data_name LIKE ?""", [data_name])
    data_present = cursor.fetchall()
    if not data_present:
        cursor.close()
        return False
    cursor.close()
    return data_present


def show_data_on_id(data_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM main_table WHERE data_id = ?""", [data_id])
    data_present = cursor.fetchone()
    if not data_present:
        cursor.close()
        return False
    cursor.close()
    return data_present


def delete_pswd(data_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM main_table WHERE data_id =:data_id', {'data_id': data_id})
    data_present = cursor.fetchone()
    if data_present is None:
        cursor.close()
        return False
    else:
        cursor.execute('DELETE FROM main_table WHERE data_id =:data_id', {'data_id': data_id})
    conn.commit()
    cursor.close()
    return True


def adm_change_data(data_id, data_name, current_data, comment, old_data):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM main_table WHERE data_id =:data_id', {'data_id': data_id})
    data_present = cursor.fetchone()
    if data_present is None:
        cursor.close()
        return False
    else:
        cursor.execute("""UPDATE main_table SET  data_name =:data_name, current_data =:current_data , comment =:comment 
                      , old_data =:old_data WHERE  data_id =:data_id 
                      """, {'data_id': data_id, 'data_name': data_name,  'current_data': current_data,
                      'old_data': old_data, 'comment': comment})
        conn.commit()
        cursor.close()
        return True


def show_history(data_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM change_log WHERE main_table_id = ?""", [data_id])
    data_present = cursor.fetchall()
    if not data_present:
        cursor.close()
        return False
    cursor.close()
    return data_present


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
        cursor.close()
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
        cursor.close()
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
def clear_guests(message):
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
        text = text+'\n'+str(user[0])+'|'+user[1]+' |Уровень доступа '+str(user[2])
    bot.send_message(message.chat.id, text)
    cursor.close()


@bot.message_handler(commands=['start', 'help'])
def start_message(message):
    global first_start
    print(message.chat.id)
    if first_start:
        user_add(message.chat.id, 'Admin')
        set_acl(message.chat.id, 0)
    acl = acl_check(message.chat.id)
    if acl > 2:
        add_guest_id(message.chat.id)
        bot.send_message(message.chat.id, 'Ошибка доступа')
        return
    bot.send_message(message.chat.id, HELP_TEXT)
    if acl < 1:
        bot.send_message(message.chat.id, ADMIN_HELP_TEXT)


@bot.message_handler(commands=['addpswd'])
def add_pswd(message):
    acl = acl_check(message.chat.id)
    if acl > 1:
        return
    message_string = message.text[8:].lstrip(' ')
    sep = message_string[0]
    tmp = cut_str(message_string[1:], sep)
    data_name = tmp[1]
    tmp = cut_str(tmp[0], sep)
    current_data = tmp[1]
    tmp = cut_str(tmp[0], sep)
    comment = tmp[1]
    old_data = tmp[0]
    new_data(data_name, current_data, comment, old_data)


@bot.message_handler(commands=['changepswd'])
def change_pswd(message):
    acl = acl_check(message.chat.id)
    if acl > 1:
        return
    message_string = message.text[12:].lstrip(' ')
    sep = message_string[0]
    tmp = cut_str(message_string[1:], sep)
    data_id = tmp[1]
    if not data_id.isdigit():
        bot.send_message(message.chat.id, 'Неправильный формат команды')
        return
    data_id = int(tmp[1])
    tmp = cut_str(tmp[0], sep)
    new_data = tmp[1]
    comment = tmp[0]
    change_data(data_id, new_data, comment, message.chat.id)
    data = show_data_on_id(data_id)
    output_string = str(data[0]) + '|' + data[1] + '|' + data[2] + '|' + data[3] + '| старые пароли ' + data[4]
    bot.send_message(message.chat.id, output_string)
    add_message_in_list(message.message_id+1, message.chat.id, int(time())+300)


@bot.message_handler(commands=['show'])
def show_pswd(message):
    acl = acl_check(message.chat.id)
    if acl > 2:
        return
    data_str = message.text[5:].lstrip(' ')
    if not data_str.isdigit():
        bot.send_message(message.chat.id, 'Неправильный формат запроса')
        return
    data_id = int(data_str)
    data = show_data_on_id(data_id)
    if data:
        output_string = str(data[0]) + '|' + data[1] + '|' + data[2] + '|' + data[3] + '| старые пароли ' + data[4]
        bot.send_message(message.chat.id, output_string)
    else:
        bot.send_message(message.chat.id, 'Индекс не найден')
    add_message_in_list(message.message_id+1, message.chat.id, int(time())+300)


@bot.message_handler(commands=['find'])
def find_pswd(message):
    acl = acl_check(message.chat.id)
    if acl > 2:
        return
    if len(message.text) == 5:
        bot.send_message(message.chat.id, 'Неуказано название для поиска')
        return
    data_name = '%' + message.text[5:].lstrip(' ') + '%'
    data_list = find_data(data_name)
    output_string = ''
    if data_list:
        for data in data_list:
            output_string = output_string + str(data[0]) + '|' + data[1] + '|' + data[2] + '\n'
        bot.send_message(message.chat.id, output_string)
    else:
        bot.send_message(message.chat.id, 'Совпадений не найдено')
    add_message_in_list(message.message_id+1, message.chat.id, int(time())+300)


@bot.message_handler(commands=['delpswd'])
def delete_pswd(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    data_str = message.text[5:].lstrip(' ')
    if not data_str.isdigit():
        bot.send_message(message.chat.id, 'Неправильный формат запроса')
        return
    data_id = int(data_str)
    data_is_deleted = delete_pswd(data_id)
    if data_is_deleted:
        bot.send_message(message.chat.id, 'Строка удалена')
    else:
        bot.send_message(message.chat.id, 'Строка не найдена')


@bot.message_handler(commands=['changedata'])
def change_data(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    message_string = message.text[11:].lstrip(' ')
    sep = message_string[0]
    tmp = cut_str(message_string[1:], sep)
    data_id = tmp[1]
    tmp = cut_str(tmp[0], sep)
    data_name = tmp[1]
    tmp = cut_str(tmp[0], sep)
    current_data = tmp[1]
    tmp = cut_str(tmp[0], sep)
    comment = tmp[1]
    old_data = tmp[0]
    data_present = adm_change_data(data_id, data_name, current_data, comment, old_data)
    if not data_present:
        bot.send_message(message.chat.id, 'Строка не найдена')
        return
    data = show_data_on_id(data_id)
    output_string = str(data[0]) + '|' + data[1] + '|' + data[2] + '|' + data[3] + '| старые пароли ' + data[4]
    bot.send_message(message.chat.id, output_string)
    add_message_in_list(message.message_id+1, message.chat.id, int(time())+300)


@bot.message_handler(commands=['history'])
def history_pswd(message):
    acl = acl_check(message.chat.id)
    if acl > 0:
        return
    data_str = message.text[8:].lstrip(' ')
    if not data_str.isdigit():
        bot.send_message(message.chat.id, 'Неправильный формат запроса')
        return
    data_id = int(data_str)
    history_list = show_history(data_id)
    output_string = ''
    if history_list:
        for data in history_list:
            output_string = output_string + str(data[0]) + '|' + str(data[1]) + '|' + data[2] +\
                            '|' + data[3] + '|' + data[4] + '\n'
        bot.send_message(message.chat.id, output_string)
    else:
        bot.send_message(message.chat.id, 'Совпадений не найдено')
    add_message_in_list(message.message_id+1, message.chat.id, int(time())+300)


def cut_str(string, separator):
    index = string.find(separator)
    data = string[0:index]
    string = string[index+1:]
    return string, data


def add_message_in_list(message_id, chat_id, message_time):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    entities = (message_id, chat_id, message_time)
    cursor.execute("""INSERT INTO message_list(message_id, chat_id, message_time) VALUES(?, ?, ?) """, entities)
    conn.commit()
    cursor.close()


def delete_message():
    while True:
        sleep_time = 300
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM message_list')
        message_list = cursor.fetchall()
        for message in message_list:
            if message[3] < int(time()):
                bot.delete_message(message[2], message[1])
                cursor.execute('DELETE FROM message_list WHERE id =:id', {'id': message[0]})
            elif sleep_time > message[3] - int(time()):
                sleep_time = message[3] - int(time())
        conn.commit()
        cursor.close()
        sleep(sleep_time)


def init_db():
    global first_start
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS message_list(id integer PRIMARY KEY, message_id integer,
                            chat_id integer, message_time integer)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS users(id integer, name text, rights integer)
                       """)
        cursor.execute("""CREATE TABLE IF NOT EXISTS guests(id integer, last_connect text)
                      """)
        cursor.execute("""CREATE TABLE IF NOT EXISTS main_table(data_id integer PRIMARY KEY,data_name text,
                           current_data text,comment text, old_data text)
                       """)
        cursor.execute("""CREATE TABLE IF NOT EXISTS change_log(log_id integer PRIMARY KEY, user_id integer,
                           date_log text, old_data text, new_data text, main_table_id integer)
                       """)
    except Exception:
        print(0)
    cursor.execute('SELECT rights FROM users')
    right_num = cursor.fetchone()
    if right_num is not None:
        first_start = False
    print(first_start)
    conn.commit()
    cursor.close()


if __name__ == "__main__":
    init_db()

    p1 = Process(target=delete_message, args=())
    p1.start()

    while True:
        try:
            bot.polling(none_stop=True, timeout=123)
        except Exception as e:
            print(e)
            sleep(15)
