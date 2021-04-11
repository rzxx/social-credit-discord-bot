import sqlite3

def sql_create_connection(dbfile):
    conn = None
    try:
        conn = sqlite3.connect(dbfile)
    except sqlite3.Error as err:
        print("Произошла ошибка! | ",err)
    finally:
        return conn

def sql_create_table(conn):
    try:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
                        id INT PRIMARY KEY,
                        name TEXT,
                        score INT,
                        voted INT,
                        lastvotedate DATE
                        );""")
    except sqlite3.Error as err:
        print("Произошла ошибка! | ",err)

database = "database.db"
conn = sql_create_connection(database)
if conn is not None:
    sql_create_table(conn)
    print("База данных успешно создана!")
else:
    print("Произошла ошибка! Не создано соединение с базой данных!")