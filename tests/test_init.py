import pytest
from django.db import connection


def test_init():
    assert True


@pytest.mark.django_db
def test_db():
    cursor = connection.cursor()
    cursor.execute("select 1 from pg_tables;")
