from django.db import connection


def test_init():
    assert True


def test_db():
    cursor = connection.cursor()
    cursor.execute("select 1 from pg_tables;")
