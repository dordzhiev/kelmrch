import re
from config import load_config
import psycopg2
import psycopg2.errors
from docx import Document as Doc


def recreate_tables(cur):
    cur.execute('DROP TABLE IF EXISTS words_translations_k1 CASCADE')
    cur.execute('DROP TABLE IF EXISTS extra_words_from_wd_k1 CASCADE')

    cur.execute('''CREATE TABLE IF NOT EXISTS words_translations_k1 (
    id serial primary key,
    word text not null,
    translation text not null,
    reference text
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS extra_words_from_wd_k1 (
    id serial primary key,
    wt_id integer references words_translations_k1,
    word text
    )''')


def wt_insert(cur, separated):
    cur.execute(
        '''INSERT INTO words_translations_k1 (word, translation, reference) 
        VALUES (%s, %s, %s) RETURNING id''',
        (separated['word'], separated['translation'], separated['reference'])
    )
    return cur.fetchone()


def ew_insert(cur, _id, separated):
    for ew in separated['extra_words']:
        cur.execute(
            '''INSERT INTO extra_words_from_wd_k1 (wt_id, word)
            VALUES (%s, %s)''',
            (_id, ew)
        )


def parse_bold(itr):
    result = ''
    temp_str = ''

    for run in itr:
        if run.bold:
            is_word = re.search(r'([а-яА-ЯёөүәҗһңӨҮӘҖҺ]+)', run.text)
            if temp_str:
                if is_word:
                    result += temp_str + run.text
                    temp_str = ''
                else:
                    return result, temp_str + run.text
            else:
                if is_word:
                    result += run.text
                else:
                    temp_str += run.text
        else:
            is_word = re.search(r'[а-яА-ЯёөүәҗһңӨҮӘҖҺ;]+?', run.text)
            if is_word:
                return result, temp_str + run.text
            else:
                temp_str += run.text
    return result, temp_str


def html_bold(some_str) -> str:
    return f'<b>{some_str}</b>'


def only_words_in_key(key, value):
    have_digits = re.search(r'(\d+)[\s.]*?$', key)
    if have_digits:
        value = html_bold(key[have_digits.regs[0][0]:]) + value
        key = key[:have_digits.regs[0][0]]
    return key, value


def split_line(runs):
    itr = iter(runs)
    word, translation = only_words_in_key(*parse_bold(itr))
    if len(word) == 0:
        raise KeyError('Не удалось спарсить ключ')
    extra_words = list()
    reference = None
    for run in itr:
        referenced = re.search(r'\b((от)|(см))\b.{,2}$', translation)
        if referenced:
            if run.bold:
                bold_word, rest = parse_bold(itr)
                bold_word = run.text + bold_word
                reference = bold_word.strip()
                translation += html_bold(bold_word) + rest
            else:
                translation += run.text
        elif run.bold:
            ext_word = run.text
            bold_word, rest = parse_bold(itr)
            ext_word += bold_word
            translation += html_bold(ext_word) + rest
            extra_words.append(ext_word.strip())
        else:
            translation += run.text
    return {
        'word': word.strip(),
        'translation': translation.strip(),
        'reference': reference,
        'extra_words': extra_words,
    }


def main():
    with open('new_document.docx', 'rb') as f:
        document = Doc(f)
    paragraphs = document.paragraphs
    config = load_config()
    con = psycopg2.connect(f"dbname={config.database.dbname} "
                           f"user={config.database.user} "
                           f"password={config.database.password}")
    cur = con.cursor()
    recreate_tables(cur)
    for paragraph in paragraphs:
        separated = split_line(paragraph.runs)  # word, translation, reference, extra_words
        _id = wt_insert(cur, separated)
        ew_insert(cur, _id, separated)
    con.commit()
    cur.close()
    con.close()


if __name__ == '__main__':
    main()
