import time

import psycopg2
from psycopg2 import OperationalError


def wait_for_postgres(
    host: str, port: int, user: str, password: str, db: str, timeout: int = 60
) -> None:
    start_time = time.time()
    while True:
        try:
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, database=db)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            cursor.close()
            conn.close()
            break
        except OperationalError:
            if time.time() - start_time >= timeout:
                raise TimeoutError  # noqa: B904
            time.sleep(0.1)


if __name__ == "__main__":
    wait_for_postgres(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_password",
        db="test_db",
    )
