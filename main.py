import os
from CinemaDatabaseCreator import CinemaDatabaseCreator

def main():
    db_creator = CinemaDatabaseCreator(
        host=os.getenv("DB_HOST", "db"),
        dbname=os.getenv("DB_NAME", "kino"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "pswd"),
        port=int(os.getenv("DB_PORT", 5432))
    )
    db_creator.create_tables()
    print("Baza danych i tabele zostały utworzone.")
    db_creator.close()


if __name__ == "__main__":
    main()
