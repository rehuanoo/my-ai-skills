# -*- coding: utf-8 -*-
"""
初始化演示用的 SQLite 用户表。
    python db/init_db.py

首次运行 server.py 之前执行一次即可。密码为明文仅用于本地演示，
真实项目请使用哈希（如 bcrypt / passlib）。
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'database.db')

DEMO_USER = ('admin', '123456')


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    cur.execute('SELECT 1 FROM user WHERE username = ?', (DEMO_USER[0],))
    if cur.fetchone() is None:
        cur.execute('INSERT INTO user (username, password) VALUES (?, ?)', DEMO_USER)
        print(f'已创建演示账号 {DEMO_USER[0]} / {DEMO_USER[1]}')
    else:
        print('演示账号已存在，跳过')
    conn.commit()
    cur.close()
    conn.close()
    print(f'数据库就绪：{DB_PATH}')


if __name__ == '__main__':
    main()
