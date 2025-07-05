from flask import Flask, render_template, jsonify, request
import sqlite3
import re
import traceback
import os
import logging

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bible_cht.sqlite3')

# 設定 logging
log_level = logging.DEBUG if os.environ.get('FLASK_ENV') == 'development' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
)
logger = logging.getLogger(__name__)

def get_db():
    logger.debug(f'連接資料庫: {DB_PATH}')
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_book_names():
    try:
        logger.debug('查詢所有書卷名稱')
        # 傳統聖經順序
        bible_order = [
            '創世記','出埃及記','利未記','民數記','申命記','約書亞記','士師記','路得記','撒母耳記上','撒母耳記下',
            '列王紀上','列王紀下','歷代志上','歷代志下','以斯拉記','尼希米記','以斯帖記','約伯記','詩篇','箴言',
            '傳道書','雅歌','以賽亞書','耶利米書','耶利米哀歌','以西結書','但以理書','何西阿書','約珥書','阿摩司書',
            '俄巴底亞書','約拿書','彌迦書','那鴻書','哈巴谷書','西番雅書','哈該書','撒迦利亞書','瑪拉基書',
            '馬太福音','馬可福音','路加福音','約翰福音','使徒行傳','羅馬書','哥林多前書','哥林多後書','加拉太書',
            '以弗所書','腓立比書','歌羅西書','帖撒羅尼迦前書','帖撒羅尼迦後書','提摩太前書','提摩太後書','提多書',
            '腓利門書','希伯來書','雅各書','彼得前書','彼得後書','約翰一書','約翰二書','約翰三書','猶大書','啟示錄'
        ]
        conn = get_db()
        cur = conn.execute('SELECT DISTINCT book_name FROM bible')
        books = [row['book_name'] for row in cur.fetchall()]
        conn.close()
        # 依照 bible_order 排序，未列入的放最後
        books_sorted = sorted(books, key=lambda x: bible_order.index(x) if x in bible_order else 999)
        logger.debug(f'查詢結果: {books_sorted}')
        return books_sorted
    except Exception as e:
        logger.error(f'get_book_names error: {e}', exc_info=True)
        return []

def get_chapters(book_name):
    try:
        logger.debug(f'查詢書卷 {book_name} 的所有章')
        conn = get_db()
        cur = conn.execute('SELECT DISTINCT chapter FROM bible WHERE book_name=? ORDER BY chapter', (book_name.strip(),))
        chapters = [row['chapter'] for row in cur.fetchall()]
        conn.close()
        logger.debug(f'查詢結果: {chapters}')
        return chapters
    except Exception as e:
        logger.error(f'get_chapters error: {e}', exc_info=True)
        return []

def get_verses(book_name, chapter):
    try:
        logger.debug(f'查詢 {book_name} 第{chapter}章的所有節')
        conn = get_db()
        cur = conn.execute('SELECT verse FROM bible WHERE book_name=? AND chapter=? ORDER BY verse', (book_name.strip(), chapter))
        verses = [row['verse'] for row in cur.fetchall()]
        conn.close()
        logger.debug(f'查詢結果: {verses}')
        return verses
    except Exception as e:
        logger.error(f'get_verses error: {e}', exc_info=True)
        return []

def get_verse_text(book_name, chapter, verse):
    try:
        logger.debug(f'查詢 {book_name} 第{chapter}章第{verse}節內容')
        conn = get_db()
        cur = conn.execute('SELECT text FROM bible WHERE book_name=? AND chapter=? AND verse=?', (book_name.strip(), chapter, verse))
        row = cur.fetchone()
        conn.close()
        logger.debug(f'查詢結果: {row["text"] if row else None}')
        return row['text'] if row else None
    except Exception as e:
        logger.error(f'get_verse_text error: {e}', exc_info=True)
        return None

def normalize_query(query):
    # 替換全形冒號、全形數字、全形減號
    query = query.replace('：', ':').replace('－', '-').replace('—', '-')
    # 全形數字轉半形
    full2half = str.maketrans('０１２３４５６７８９', '0123456789')
    query = query.translate(full2half)
    # 新增：支援中文書卷簡寫，例如「歷下」對應「歷代志下」
    abbr_map = {
        '創': '創世記', '出': '出埃及記', '利': '利未記', '民': '民數記', '申': '申命記',
        '書': '約書亞記', '士': '士師記', '得': '路得記',
        '撒上': '撒母耳記上', '撒下': '撒母耳記下',
        '王上': '列王紀上', '王下': '列王紀下',
        '歷上': '歷代志上', '歷下': '歷代志下',
        '拉': '以斯拉記', '尼': '尼希米記', '斯': '以斯帖記',
        '伯': '約伯記', '詩': '詩篇', '箴': '箴言', '傳': '傳道書', '歌': '雅歌',
        '賽': '以賽亞書', '耶': '耶利米書', '哀': '耶利米哀歌',
        '結': '以西結書', '但': '但以理書', '何': '何西阿書', '珥': '約珥書',
        '摩': '阿摩司書', '俄': '俄巴底亞書', '拿': '約拿書', '彌': '彌迦書',
        '鴻': '那鴻書', '哈': '哈巴谷書', '番': '西番雅書', '該': '哈該書',
        '亞': '撒迦利亞書', '瑪': '瑪拉基書',
        '太': '馬太福音', '可': '馬可福音', '路': '路加福音', '約': '約翰福音',
        '徒': '使徒行傳', '羅': '羅馬書', '林前': '哥林多前書', '林後': '哥林多後書',
        '加': '加拉太書', '弗': '以弗所書', '腓': '腓立比書', '西': '歌羅西書',
        '帖前': '帖撒羅尼迦前書', '帖後': '帖撒羅尼迦後書',
        '提前': '提摩太前書', '提後': '提摩太後書',
        '多': '提多書', '門': '腓利門書', '來': '希伯來書', '雅': '雅各書',
        '彼前': '彼得前書', '彼後': '彼得後書', '約一': '約翰一書', '約二': '約翰二書', '約三': '約翰三書',
        '猶': '猶大書', '啟': '啟示錄'
    }
    # 先處理較長的鍵，避免「林前」被「林」截斷等問題
    for k in sorted(abbr_map, key=len, reverse=True):
        if query.startswith(k):
            query = abbr_map[k] + query[len(k):]
            break

    # 保留英文書卷簡寫對應
    book_map = {
        'Gen': '創世記', 'Exo': '出埃及記', 'Lev': '利未記', 'Num': '民數記', 'Deu': '申命記',
        'Jos': '約書亞記', 'Jdg': '士師記', 'Rut': '路得記', '1Sa': '撒母耳記上', '2Sa': '撒母耳記下',
        '1Ki': '列王紀上', '2Ki': '列王紀下', '1Ch': '歷代志上', '2Ch': '歷代志下', 'Ezr': '以斯拉記',
        'Neh': '尼希米記', 'Est': '以斯帖記', 'Job': '約伯記', 'Psa': '詩篇', 'Pro': '箴言',
        'Ecc': '傳道書', 'Sng': '雅歌', 'Isa': '以賽亞書', 'Jer': '耶利米書', 'Lam': '耶利米哀歌',
        'Eze': '以西結書', 'Dan': '但以理書', 'Hos': '何西阿書', 'Joe': '約珥書', 'Amo': '阿摩司書',
        'Oba': '俄巴底亞書', 'Jon': '約拿書', 'Mic': '彌迦書', 'Nah': '那鴻書', 'Hab': '哈巴谷書',
        'Zep': '西番雅書', 'Hag': '哈該書', 'Zec': '撒迦利亞書', 'Mal': '瑪拉基書',
        'Mat': '馬太福音', 'Mar': '馬可福音', 'Luk': '路加福音', 'Joh': '約翰福音',
        'Act': '使徒行傳', 'Rom': '羅馬書', '1Co': '哥林多前書', '2Co': '哥林多後書',
        'Gal': '加拉太書', 'Eph': '以弗所書', 'Phi': '腓立比書', 'Col': '歌羅西書',
        '1Th': '帖撒羅尼迦前書', '2Th': '帖撒羅尼迦後書', '1Ti': '提摩太前書', '2Ti': '提摩太後書',
        'Tit': '提多書', 'Phm': '腓利門書', 'Heb': '希伯來書', 'Jas': '雅各書',
        '1Pe': '彼得前書', '2Pe': '彼得後書', '1Jo': '約翰一書', '2Jo': '約翰二書', '3Jo': '約翰三書',
        'Jud': '猶大書', 'Rev': '啟示錄'
    }
    for k, v in book_map.items():
        if query.startswith(k):
            query = query.replace(k, v, 1)
            break

    return query

def search_bible(query):
    try:
        query = normalize_query(query)
        logger.debug(f'search_bible 查詢: {query}')
        conn = get_db()
        results = []
        pattern_single = r'([\u4e00-\u9fa5]{1,5})(\d+):(\d+)$'
        pattern_range = r'([\u4e00-\u9fa5]{1,5})(\d+):(\d+)-(\d+)$'
        pattern_chapter = r'([\u4e00-\u9fa5]{1,5})(\d+)$'  # 新增只查章
        match_range = re.match(pattern_range, query)
        match_single = re.match(pattern_single, query)
        match_chapter = re.match(pattern_chapter, query)
        if match_range:
            book_prefix, chapter, verse_start, verse_end = match_range.groups()
            logger.debug(f'範圍查詢: {book_prefix} {chapter}:{verse_start}-{verse_end}')
            cur = conn.execute('SELECT DISTINCT book_name FROM bible WHERE (book_name LIKE ? OR book LIKE ?) ORDER BY LENGTH(book_name) DESC', (f'%{book_prefix}%', f'%{book_prefix}%'))
            book_rows = cur.fetchall()
            for book_row in book_rows:
                book_name = book_row['book_name']
                cur2 = conn.execute('SELECT COUNT(1) as cnt FROM bible WHERE book_name=? AND chapter=? AND verse>=? AND verse<=?', (book_name, int(chapter), int(verse_start), int(verse_end)))
                row2 = cur2.fetchone()
                if row2 and row2['cnt'] > 0:
                    logger.debug(f'找到: {book_name} {chapter}:{verse_start}-{verse_end}')
                    results.append({
                        'book': book_name,
                        'chapter': int(chapter),
                        'verse_start': int(verse_start),
                        'verse_end': int(verse_end),
                        'type': 'range'
                    })
        elif match_single:
            book_prefix, chapter, verse = match_single.groups()
            logger.debug(f'單節查詢: {book_prefix} {chapter}:{verse}')
            cur = conn.execute('SELECT DISTINCT book_name FROM bible WHERE (book_name LIKE ? OR book LIKE ?) ORDER BY LENGTH(book_name) DESC', (f'%{book_prefix}%', f'%{book_prefix}%'))
            book_rows = cur.fetchall()
            for book_row in book_rows:
                book_name = book_row['book_name']
                cur2 = conn.execute('SELECT COUNT(1) as cnt FROM bible WHERE book_name=? AND chapter=? AND verse=?', (book_name, int(chapter), int(verse)))
                row2 = cur2.fetchone()
                if row2 and row2['cnt'] > 0:
                    logger.debug(f'找到: {book_name} {chapter}:{verse}')
                    results.append({
                        'book': book_name,
                        'chapter': int(chapter),
                        'verse': int(verse),
                        'type': 'single'
                    })
        elif match_chapter:
            book_prefix, chapter = match_chapter.groups()
            logger.debug(f'章查詢: {book_prefix} {chapter}')
            cur = conn.execute('SELECT DISTINCT book_name FROM bible WHERE (book_name LIKE ? OR book LIKE ?) ORDER BY LENGTH(book_name) DESC', (f'%{book_prefix}%', f'%{book_prefix}%'))
            book_rows = cur.fetchall()
            for book_row in book_rows:
                book_name = book_row['book_name']
                cur2 = conn.execute('SELECT COUNT(1) as cnt FROM bible WHERE book_name=? AND chapter=?', (book_name, int(chapter)))
                row2 = cur2.fetchone()
                if row2 and row2['cnt'] > 0:
                    logger.debug(f'找到: {book_name} {chapter}章')
                    results.append({
                        'book': book_name,
                        'chapter': int(chapter),
                        'type': 'chapter'
                    })
        else:
            logger.debug(f'模糊查詢: {query}')
            cur = conn.execute('SELECT DISTINCT book_name FROM bible WHERE book_name LIKE ? ORDER BY book_name', (f'%{query}%',))
            for row in cur.fetchall():
                logger.debug(f'模糊命中: {row["book_name"]}')
                results.append({'book': row['book_name'], 'type': 'book'})
        conn.close()
        logger.debug(f'search_bible 結果: {results}')
        return results
    except Exception as e:
        logger.error(f'search_bible error: {e}', exc_info=True)
        return []

@app.route('/')
def index():
    logger.info('訪問首頁 /')
    return render_template('index.html')

@app.route('/api/books')
def get_books():
    try:
        logger.info('API /api/books')
        return jsonify(get_book_names())
    except Exception as e:
        logger.error('/api/books error: %s', e, exc_info=True)
        return jsonify([])

@app.route('/api/chapters/<book_name>')
def get_chapters_api(book_name):
    try:
        logger.info(f'API /api/chapters/{book_name}')
        return jsonify(get_chapters(book_name))
    except Exception as e:
        logger.error('/api/chapters error: %s', e, exc_info=True)
        return jsonify([])

@app.route('/api/verses/<book_name>/<int:chapter>')
def get_verses_api(book_name, chapter):
    try:
        logger.info(f'API /api/verses/{book_name}/{chapter}')
        return jsonify(get_verses(book_name, chapter))
    except Exception as e:
        logger.error('/api/verses error: %s', e, exc_info=True)
        return jsonify([])

@app.route('/api/verse/<book_name>/<int:chapter>/<int:verse>')
def get_verse_api(book_name, chapter, verse):
    try:
        logger.info(f'API /api/verse/{book_name}/{chapter}/{verse}')
        text = get_verse_text(book_name, chapter, verse)
        if text:
            return jsonify({
                'book': book_name,
                'chapter': chapter,
                'verse': verse,
                'text': text
            })
        logger.warning(f'找不到經文: {book_name} {chapter}:{verse}')
        return jsonify({'error': 'Verse not found'}), 404
    except Exception as e:
        logger.error('/api/verse error: %s', e, exc_info=True)
        return jsonify({'error': 'Server error'}), 500

@app.route('/api/search')
def search():
    try:
        query = request.args.get('q', '')
        logger.info(f'API /api/search?q={query}')
        results = search_bible(query)
        return jsonify(results)
    except Exception as e:
        logger.error('/api/search error: %s', e, exc_info=True)
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True) 