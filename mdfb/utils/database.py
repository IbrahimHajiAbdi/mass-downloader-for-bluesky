import sqlite3
import platformdirs
import os
import logging
import threading

class Database():
    def __init__(self, logger: logging.Logger = None):
        self.db_path = platformdirs.user_data_dir(appname="mdfb")
        self._ensure_database_exists()
        self.logger = logger or logging.getLogger(__name__)
        self._local = threading.local()

    def _ensure_database_exists(self):
        if not os.path.isdir(self.db_path):
            path = platformdirs.user_data_dir(appname="mdfb", ensure_exists=True)
            logging.info(f"Creating database as the mdfb directory [{path}] does not exist...")
        elif os.path.isdir(self.db_path) and not os.path.isfile(os.path.join(platformdirs.user_data_path(appname="mdfb"), "mdfb.db")):
            logging.info("Creating database as the mdfb directory does exist, but there is no database...")
        
        con = sqlite3.connect(os.path.join(self.db_path, "mdfb.db"))
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS downloaded_posts (
                user_did TEXT NOT NULL,
                user_post_uri TEXT NOT NULL,
                feed_type TEXT NOT NULL,
                poster_post_uri TEXT NOT NULL,
                PRIMARY KEY (user_post_uri, user_did, feed_type)
            );
        """)
        con.commit()
        con.close()
    
    @property
    def connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection"):
            db_file_path = os.path.join(self.db_path, "mdfb.db")
            self._local.connection = sqlite3.connect(db_file_path)
            thread_name = threading.current_thread().name
            self.logger.info(f"Created database connection for thread: {thread_name}")
        return self._local.connection

    @property
    def cursor(self) -> sqlite3.Cursor:
        return self.connection.cursor()

    def insert_post(self, rows: list[tuple]) -> bool:
        res = self.cursor.executemany("""
            INSERT OR IGNORE INTO downloaded_posts (user_did, user_post_uri, feed_type, poster_post_uri) 
            VALUES (?, ?, ?, ?)
        """, rows)
        
        if res.rowcount > 0:
            return True
        return False

    def check_post_exists(self, user_did: str, user_post_uri: str, feed_type: str) -> bool:
        res = self.cursor.execute("""
            SELECT * FROM downloaded_posts 
            WHERE user_did = ? 
            AND user_post_uri = ?
            AND feed_type = ?
        """, (user_did, user_post_uri, feed_type))

        row = res.fetchone()
        if row:
            return True
        return False

    def check_user_has_posts(self, user_did: str, feed_type: str) -> bool:
        res = self.cursor.execute("""
            SELECT * FROM downloaded_posts
            WHERE user_did = ?
            AND feed_type = ?
        """, [user_did, feed_type])

        row = res.fetchone()
        if row:
            return True
        return False

    def check_user_exists(self, did: str) -> bool:
        cur = self.cursor
        res = cur.execute("""
            SELECT * FROM downloaded_posts
            WHERE user_did = ?
        """, (did,))

        row = res.fetchone()
        if row:
            return True
        return False

    def delete_user(self, did: str):
        cur = self.cursor
        cur.execute("""
            DELETE FROM downloaded_posts
            WHERE user_did = ?
        """, (did,))
        self.connection.commit()

        if cur.rowcount > 0:
            print(f"Deleted {cur.rowcount} row(s)")
        else:
            print("No matching rows found to delete")

    def restore_posts(self, did: str, post_types: dict) -> list[dict]:
        def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row):
            fields = [column[0] for column in cursor.description]
            return {key: value for key, value in zip(fields, row)}

        con = self.connection
        con.row_factory = _dict_factory
        cur = con.cursor()

        uris = []
        conditions = []
        params = []
        query = "SELECT * FROM downloaded_posts"

        if did:
            conditions.append("user_did = ?")
            params.append(did)
        if post_types:
            selected_post_types = [post_type for post_type, wanted in post_types.items() if wanted]
            if selected_post_types:
                conditions.append("feed_type IN ({})".format(",".join(["?"] * len(selected_post_types))))
                params.extend(selected_post_types)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = cur.execute(query, params)
        for row in rows:
            row["user_post_uri"] = [row["user_post_uri"]]
            row["feed_type"] = [row["feed_type"]]
            uris.append(row)

        con.row_factory = None

        return uris


