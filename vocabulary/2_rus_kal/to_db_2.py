import re
from config import load_config
import psycopg2
from docx import Document as Doc
from docx.text.paragraph import Paragraph


def recreate_tables(cur):
    cur.execute('DROP TABLE IF EXISTS russian_words CASCADE')
    cur.execute('DROP TABLE IF EXISTS kalmyk_translations CASCADE;')
    cur.execute('DROP TABLE IF EXISTS words_translations_2 CASCADE;')
    cur.execute('DROP TABLE IF EXISTS words_translations_r1 CASCADE;')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS words_translations_r1 (
    id serial primary key,
    word text not null,
    translation text not null,
    reference text
    )
    ''')


def wt_insert(cur, word, translation):
    cur.execute(
        '''INSERT INTO words_translations_r1 (word, translation) 
        VALUES (%s, %s) RETURNING id''',
        (word, translation)
    )
    return cur.fetchone()


def main():
    config = load_config()
    con = psycopg2.connect(f"dbname={config.database.dbname} "
                           f"user={config.database.user} "
                           f"password={config.database.password}")
    cur = con.cursor()
    recreate_tables(cur)
    with open('1174_I_1174__1240_N_E_B__1198_GIN_ERK_russko-_kalmytskiy_slovar.docx', 'rb') as f:
        document = Doc(f)
    paragraphs: list[Paragraph] = document.paragraphs
    for paragraph in paragraphs:
        text = paragraph.text
        if ' – ' in text:
            word = text[:text.find(' – ')].strip()
            translation = text[text.find(' – ') + 3:].strip()
            wt_insert(cur, word, translation)
        else:
            if '-' in text:
                print(paragraph.text)
    con.commit()


if __name__ == '__main__':
    main()
