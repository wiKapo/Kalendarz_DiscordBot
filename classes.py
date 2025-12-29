import sqlite3


class Db:
    connection = None
    cursor = None

    def fetch_one(self, query: str, data):
        self.connect()
        self.cursor.execute(query, data)
        result = self.cursor.fetchone()
        self.disconnect()
        return result

    def fetch_all(self, query: str, data):
        self.connect()
        self.cursor.execute(query, data)
        result = self.cursor.fetchall()
        self.disconnect()
        return result

    def fetch_many(self, query: str, data, amount: int):
        self.connect()
        self.cursor.execute(query, data)
        result = self.cursor.fetchmany(amount)
        self.disconnect()
        return result

    def execute(self, query: str, data=None):
        self.connect()
        if data:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        self.commit_disconnect()

    def connect(self):
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
