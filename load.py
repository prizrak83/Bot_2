import sqlite3


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


def add_data(message_string):
    sep = message_string[0]
    tmp = cut_str(message_string[1:], sep)
    data_name = tmp[1]
    tmp = cut_str(tmp[0], sep)
    current_data = tmp[1]
    tmp = cut_str(tmp[0], sep)
    comment = tmp[1]
    old_data = tmp[0]
    new_data(data_name, current_data, comment, old_data)


def cut_str(string, separator):
    index = string.find(separator)
    data = string[0:index]
    string = string[index+1:]
    return string, data


conn_init = sqlite3.connect("database.db")
cursor_init = conn_init.cursor()
try:
    cursor_init.execute("drop table main_table")
except Exception:
    print(0)
finally:
    cursor_init.execute("""CREATE TABLE main_table(data_id integer PRIMARY KEY,data_name text,
                   current_data text,comment text, old_data text)
                     """)

f = open('load.txt')
line = f.readline()
for line in f.readlines():
    add_data(line[:-1])
f.close()
