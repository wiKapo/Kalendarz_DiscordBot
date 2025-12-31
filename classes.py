import sqlite3


class Db:
    connection: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    def fetch_one(self, query: str, data=None):
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        result = self.cursor.fetchone()
        self.disconnect()
        return result

    def fetch_all(self, query: str, data=None) -> list:
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.disconnect()
        return result

    def fetch_many(self, query: str, amount: int, data=None) -> list:
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        result = self.cursor.fetchmany(amount)
        self.disconnect()
        return result

    def execute(self, query: str, data=None):
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        self.commit_disconnect()

    def connect(self) -> sqlite3.Cursor:
        self.connection = sqlite3.connect('calendar_database.db')
        self.cursor = self.connection.cursor()
        return self.cursor

    def commit(self):
        self.connection.commit()

    def commit_disconnect(self):
        self.connection.commit()
        self.disconnect()

    def disconnect(self):
        self.cursor.close()
        self.connection.close()
