from config import DB_PROVIDER


def get_active_db_provider():
    return DB_PROVIDER


def using_mongodb():
    return get_active_db_provider() == "mongodb"
