from config import load_config
import psycopg2


def recreate_tables(cur):
    cur.execute('''
    DROP TABLE IF EXISTS all_words CASCADE;
    DROP TABLE IF EXISTS all_translations CASCADE;
    DROP TABLE IF EXISTS cyrillic_aliases CASCADE;
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS all_words (
        id serial primary key,
        vocabulary varchar (1),
        word text,
        unique (vocabulary, word)
    );''')
    cur.execute('''CREATE TABLE IF NOT EXISTS all_translations (
        id serial primary key,
        aw_id integer references all_words,
        translation text
    );''')
    cur.execute('''CREATE TABLE IF NOT EXISTS cyrillic_aliases (
        id serial primary key references all_words,
        alias text
    );''')
    try:
        cur.execute('CREATE INDEX all_words_idx ON all_words USING GIST (word gist_trgm_ops);')
        cur.execute('CREATE INDEX all_translations_idx ON all_translations USING GIST (translation gist_trgm_ops);')
        cur.execute('CREATE INDEX cyrillic_aliases_idx ON cyrillic_aliases USING GIST (alias gist_trgm_ops);')
    except:
        cur.connection.rollback()
        cur.execute('CREATE EXTENSION pg_trgm;')
        recreate_tables(cur)


def unite_vocabularies(cur):
    cur.execute('''
    INSERT INTO all_words (word, vocabulary)
    SELECT DISTINCT word, vocabulary
    FROM (
        SELECT 'k' as vocabulary, word
        FROM words_translations_k1
        UNION ALL
        SELECT 'r' as vocabulary, word
        FROM words_translations_r1
    ) a
    ORDER BY word, vocabulary
    ''')
    cur.execute('''
    INSERT INTO all_translations (aw_id, translation)
    SELECT DISTINCT aw_id, translation
    FROM (
        SELECT (SELECT id FROM all_words WHERE word = wt.word AND vocabulary = 'k') as aw_id, translation
        FROM words_translations_k1 wt
        UNION ALL
        SELECT (SELECT id FROM all_words WHERE word = wt.word AND vocabulary = 'r') as aw_id, translation
        FROM words_translations_r1 wt
    ) a
    ORDER BY aw_id, translation
    ''')


def select_kalmyk_words(cur):
    cur.execute('''
    SELECT id, vocabulary, lower(word)
    FROM all_words aw
    WHERE vocabulary='k' AND word ~* '[өүәҗһң]'
    ''')
    return cur.fetchall()


if __name__ == '__main__':
    config = load_config()
    con = psycopg2.connect(
        f"dbname={config.database.dbname} "
        f"user={config.database.user} "
        f"password={config.database.password}"
    )
    cur = con.cursor()
    recreate_tables(cur)
    unite_vocabularies(cur)
    kalmyk_words = select_kalmyk_words(cur)
    for one in kalmyk_words:
        word: str = one[2]
        word = word.replace('ө', 'о')
        word = word.replace('ү', 'у')
        word = word.replace('ә', 'я')
        word = word.replace('җ', 'дж')
        word = word.replace('һ', 'гх')
        word = word.replace('ң', 'нг')
        cur.execute('INSERT INTO cyrillic_aliases (id, alias) VALUES (%s, %s)', (one[0], word))
    con.commit()
