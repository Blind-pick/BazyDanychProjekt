from CinemaDatabaseCreator import CinemaDatabaseCreator


def main():
    db_creator = CinemaDatabaseCreator(
        host="localhost",
        dbname="kino",
        user="postgres",
        password="pswd"
    )

    db_creator.create_tables()
    print("Baza danych i tabele zostały utworzone.")
    db_creator.close()


if __name__ == "__main__":
    main()
