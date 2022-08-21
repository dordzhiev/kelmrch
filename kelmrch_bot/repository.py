import dataclasses

import psycopg2
from psycopg2 import pool
from psycopg2 import extras

from kelmrch_bot.dto import Translation
from config import config


def get_and_put_conn(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        con = self.pool.getconn()
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            r = func(*args, **kwargs, cur=cur)
        self.pool.putconn(con)
        return r

    return wrapper


@dataclasses.dataclass
class Repository:

    def __init__(self, dbname, user, password):
        self.pool = pool.ThreadedConnectionPool(
            1, 4,
            dbname=dbname,
            user=user,
            password=password,
        )

    @get_and_put_conn
    def get_translations(self, word, max_offset, query_offset, cur):
        cur.execute(f'''
        SELECT
            aw.id,
            vocabulary,
            word,
            STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation,
            GREATEST ( similarity (word, %s), similarity (alias, %s) ) as sml
        FROM all_words aw INNER JOIN all_translations at2
        ON aw.id = aw_id
        LEFT JOIN cyrillic_aliases ca
        ON aw.id = ca.id
        WHERE word %% %s or alias %% %s
        GROUP BY aw.id, vocabulary, word, alias
        ORDER BY sml DESC, vocabulary, id LIMIT {max_offset} OFFSET {query_offset}
        ''', (word, word, word, word,))
        return [Translation(**row) for row in cur.fetchall()]

    @get_and_put_conn
    def get_russian_translations(self, word, max_offset, query_offset, cur):
        cur.execute(f'''
        SELECT 
            aw.id,
            vocabulary,
            word,
            STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation,
            strict_word_similarity (word, %s) as sml
        FROM all_words aw INNER JOIN all_translations at2
        ON aw.id = aw_id
        WHERE vocabulary = 'r' AND word %% %s
        GROUP BY aw.id, vocabulary, word
        ORDER BY sml DESC, id LIMIT {max_offset} OFFSET {query_offset}
        ''', (word, word))
        return [Translation(**row) for row in cur.fetchall()]

    @get_and_put_conn
    def get_kalmyk_translations(self, word, max_offset, query_offset, cur):
        cur.execute(f'''
        SELECT
            aw.id,
            vocabulary,
            word,
            STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation,
            GREATEST ( strict_word_similarity (word, %s), strict_word_similarity (alias, %s) ) as sml
        FROM all_words aw
        INNER JOIN all_translations at2
        ON aw.id = aw_id
        LEFT JOIN cyrillic_aliases ca
        ON aw.id = ca.id
        WHERE vocabulary = 'k' AND (word %% %s OR alias %% %s)
        GROUP BY aw.id, vocabulary, word, alias
        ORDER BY sml DESC, id LIMIT {max_offset} OFFSET {query_offset}
        ''', (word, word, word, word,))
        return [Translation(**row) for row in cur.fetchall()]

    @get_and_put_conn
    def get_by_id(self, _id, cur):
        cur.execute(
            f'''
            SELECT
                aw.id,
                vocabulary,
                word,
                STRING_AGG ( translation, '\n' ORDER BY at2.id ) as translation
            FROM all_words aw INNER JOIN all_translations at2
            ON aw.id = aw_id
            WHERE aw.id = {_id}
            GROUP BY aw.id, vocabulary, word
            '''
        )
        return [Translation(**row) for row in cur.fetchall()]

    @get_and_put_conn
    def get_reversed_translations(self, word, cur):
        cur.execute(
            '''
            select word, "translation", word_similarity(%s, "translation") as sml
            from all_words aw inner join all_translations at2
            on aw.id = at2.aw_id
            where %s <%% "translation"
            and "translation" ~ '(?<![а-яёөүәҗһң]\s)(?:%s)(?!\s[а-яёөүәҗһң])'
            order by sml desc
            ''',
            (word, word, word,)
        )
        return [Translation(**row) for row in cur.fetchall()]


repository = Repository(config.database.dbname, config.database.user, config.database.password)
