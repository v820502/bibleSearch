import requests
import sqlite3
import time
import random

# 書卷對照表（中文簡寫, 中文全名）
BOOKS = [
    ('創', '創世記'), ('出', '出埃及記'), ('利', '利未記'), ('民', '民數記'), ('申', '申命記'),
    ('書', '約書亞記'), ('士', '士師記'), ('得', '路得記'), ('撒上', '撒母耳記上'), ('撒下', '撒母耳記下'),
    ('王上', '列王紀上'), ('王下', '列王紀下'), ('代上', '歷代志上'), ('代下', '歷代志下'), ('拉', '以斯拉記'),
    ('尼', '尼希米記'), ('斯', '以斯帖記'), ('伯', '約伯記'), ('詩', '詩篇'), ('箴', '箴言'),
    ('傳', '傳道書'), ('歌', '雅歌'), ('賽', '以賽亞書'), ('耶', '耶利米書'), ('哀', '耶利米哀歌'),
    ('結', '以西結書'), ('但', '但以理書'), ('何', '何西阿書'), ('珥', '約珥書'), ('摩', '阿摩司書'),
    ('俄', '俄巴底亞書'), ('拿', '約拿書'), ('彌', '彌迦書'), ('鴻', '那鴻書'), ('哈', '哈巴谷書'),
    ('番', '西番雅書'), ('該', '哈該書'), ('亞', '撒迦利亞書'), ('瑪', '瑪拉基書'),
    ('太', '馬太福音'), ('可', '馬可福音'), ('路', '路加福音'), ('約', '約翰福音'), ('徒', '使徒行傳'),
    ('羅', '羅馬書'), ('林前', '哥林多前書'), ('林後', '哥林多後書'), ('加', '加拉太書'), ('弗', '以弗所書'),
    ('腓', '腓立比書'), ('西', '歌羅西書'), ('帖前', '帖撒羅尼迦前書'), ('帖後', '帖撒羅尼迦後書'), ('提前', '提摩太前書'),
    ('提後', '提摩太後書'), ('多', '提多書'), ('門', '腓利門書'), ('來', '希伯來書'), ('雅', '雅各書'),
    ('彼前', '彼得前書'), ('彼後', '彼得後書'), ('約一', '約翰一書'), ('約二', '約翰二書'), ('約三', '約翰三書'),
    ('猶', '猶大書'), ('啟', '啟示錄')
]

DB_PATH = 'bible_search/bible_cht.sqlite3'
API_URL = 'https://bible.fhl.net/json/qb.php'

# 建立資料庫
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''
DROP TABLE IF EXISTS bible;
''')
c.execute('''
CREATE TABLE IF NOT EXISTS bible (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book TEXT,
    book_name TEXT,
    chapter INTEGER,
    verse INTEGER,
    text TEXT
)
''')
conn.commit()

def fetch_chapter(book, book_name, chapter):
    params = {
        'chineses': book,
        'chap': chapter,
        'gb': 0,  # 0=繁體
        'version': 'unv'  # 和合本
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        data = resp.json()
        if data['record_count'] > 0:
            for rec in data['record']:
                c.execute('INSERT INTO bible (book, book_name, chapter, verse, text) VALUES (?, ?, ?, ?, ?)',
                          (book, book_name, int(rec['chap']), int(rec['sec']), rec['bible_text']))
            conn.commit()
            print(f"{book_name} 第{chapter}章 完成")
            return True
        else:
            print(f"{book_name} 第{chapter}章 無資料，視為結束")
            return False
    except Exception as e:
        print(f"{book_name} 第{chapter}章 失敗: {e}")
        time.sleep(2)
        return fetch_chapter(book, book_name, chapter)

def fetch_all():
    for book, book_name in BOOKS:
        chapter = 1
        while True:
            has_data = fetch_chapter(book, book_name, chapter)
            if not has_data:
                break
            chapter += 1
            time.sleep(0.5)

if __name__ == '__main__':
    fetch_all()
    print('全部完成！')
    conn.close() 