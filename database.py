import sqlite3
import logging
from random import randint


def clean(SQL_str):
    return SQL_str[2:-3:]


def clean_price(SQL_str):
    return SQL_str[1::]


def get_list_of_files_in_category(category=None):
    if category:
        result = []
        database = sqlite3.connect("files_db")
        cur = database.cursor()
        database.row_factory = lambda cursor, row: row[0]
        res = cur.execute("SELECT name FROM files WHERE category = ?;", [category]).fetchall()
        logging.info("list of files have been delivered")
        for i in res:
            result.append(clean(str(i)))
        database.close()
        return result
    else:
        result = []
        database = sqlite3.connect("files_db")
        cur = database.cursor()
        database.row_factory = lambda cursor, row: row[0]
        res = cur.execute("SELECT name FROM files;")
        logging.info("list of files have been delivered")
        for i in res:
            result.append(clean(str(i)))
        database.close()
        return result


def get_price(name):
    database = sqlite3.connect("files_db")
    cur = database.cursor()
    price = cur.execute("SELECT price FROM files WHERE name = ?;", [name]).fetchall()
    database.commit()
    database.close()
    logging.info("retrieval have been done")
    return clean(str(price))


def insert(name, category, price):
    if category is None:
        category = 'Другое'
    if price is None:
        price = 0
    database = sqlite3.connect("files_db")
    cur = database.cursor()
    cur.execute("INSERT OR REPLACE INTO files(name, category, price) VALUES(?, ?, ?);", (name, category, price))
    database.commit()
    database.close()
    logging.info("insertion have been done")


def retrieve(name):
    database = sqlite3.connect("files_db")
    cur = database.cursor()
    file = cur.execute("SELECT * FROM files WHERE name = ?;", [name])
    database.commit()
    database.close()
    logging.info("retrieval have been done")
    return clean(str(file))


def find(search):
    result = []
    database = sqlite3.connect("files_db")
    cur = database.cursor()
    database.row_factory = lambda cursor, row: row[0]
    res = cur.execute("SELECT name FROM files WHERE name LIKE ?;", ["%"+search+"%"])
    logging.info("list of files have been delivered")
    for i in res:
        result.append(clean(str(i)))
    database.close()
    return result


print(find('друг'))


def delete(name):
    database = sqlite3.connect("files_db")
    cur = database.cursor()
    cur.execute("DELETE FROM files WHERE name = ?;", [name])
    database.commit()
    database.close()
    logging.info("removal have been commenced")


def get_test_files(category=None):
    database = sqlite3.connect("files_db")
    cur = database.cursor()
    cur.execute('''
              CREATE TABLE IF NOT EXISTS files
              ([name] TEXT PRIMARY KEY, [category] TEXT, [price] INTEGER)
              ''')

    cur.execute('''
              INSERT OR REPLACE INTO files (name, category, price)
                    VALUES
                    ('общие 1', 'Общие заявления по ГПК РФ', ?),
                    ('семья 1', 'Заявления по семейным спорам', ?),
                    ('наследство 1', 'Заявления по наследственным спорам', ?),
                    ('труд 1', 'Заявления по трудовым спорам', ?),
                    ('друг 1', 'Другое', ?);
              ''',
                (randint(100, 1000), randint(100, 1000), randint(100, 1000), randint(100, 1000), randint(100, 1000)))
    database.commit()
    database.close()


def create_test_files():
    list_of_files = get_list_of_files_in_category()
    for file in list_of_files:
        with open(f'Files/{file}', 'w') as f:
            f.write('Create a new text file!')

# get_test_files()
# create_test_files()

# print(get_list_of_files_in_category())
