# logic.py
import sqlite3
from config import DATABASE

class DB_Manager:
    def __init__(self, database: str):
        self.database = database
        # при первом запуске:
        # self.create_tables()
        # self.default_insert()

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS status (
                    status_id   INTEGER PRIMARY KEY,
                    status_name TEXT UNIQUE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    skill_id   INTEGER PRIMARY KEY,
                    skill_name TEXT UNIQUE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    project_id   INTEGER PRIMARY KEY,
                    user_id      INTEGER,
                    project_name TEXT,
                    description  TEXT,
                    url          TEXT,
                    status_id    INTEGER,
                    photo        TEXT,
                    FOREIGN KEY(status_id) REFERENCES status(status_id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_skills (
                    project_id INTEGER,
                    skill_id   INTEGER,
                    UNIQUE(project_id, skill_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(skill_id)   REFERENCES skills(skill_id)
                )
            ''')
            conn.commit()

    def __executemany(self, sql: str, data: list[tuple]):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany(sql, data)

    def __select(self, sql: str, params: tuple=()) -> list[tuple]:
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()

    def default_insert(self):
        """Заполнить справочники статусов и навыков."""
        statuses = [
            ('На этапе проектирования',),
            ('В процессе разработки',),
            ('Разработан. Готов к использованию.',),
            ('Обновлен',),
            ('Завершен. Не поддерживается',),
        ]
        skills = [
            ('Python',), ('SQL',), ('API',), ('Telegram',)
        ]
        self.__executemany(
            "INSERT OR IGNORE INTO status (status_name) VALUES(?)",
            statuses
        )
        self.__executemany(
            "INSERT OR IGNORE INTO skills (skill_name) VALUES(?)",
            skills
        )

    # ------ Insert / Update ------

    def insert_project(self, data: list[tuple]):
        self.__executemany(
            "INSERT OR IGNORE INTO projects (user_id, project_name, url, status_id) VALUES(?,?,?,?)",
            data
        )

    def insert_skill(self, user_id: int, project_name: str, skill: str):
        pid = self.get_project_id(project_name, user_id)
        sid = self.__select(
            "SELECT skill_id FROM skills WHERE skill_name=?", (skill,)
        )[0][0]
        self.__executemany(
            "INSERT OR IGNORE INTO project_skills VALUES(?,?)",
            [(pid, sid)]
        )

    def update_projects(self, column: str, data: tuple):
        """
        data = (new_value, project_name, user_id)
        """
        sql = f"UPDATE projects SET {column}=? WHERE project_name=? AND user_id=?"
        self.__executemany(sql, [data])

    def update_skill(self, old: str, new: str):
        self.__executemany(
            "UPDATE skills SET skill_name=? WHERE skill_name=?", [(new, old)]
        )

    def update_status(self, old: str, new: str):
        self.__executemany(
            "UPDATE status SET status_name=? WHERE status_name=?", [(new, old)]
        )

    # ------ Delete ------

    def delete_project(self, user_id: int, project_id: int):
        self.__executemany(
            "DELETE FROM projects WHERE user_id=? AND project_id=?",
            [(user_id, project_id)]
        )

    def delete_skill(self, project_id: int, skill_id: int):
        self.__executemany(
            "DELETE FROM project_skills WHERE project_id=? AND skill_id=?",
            [(project_id, skill_id)]
        )

    # ------ Select ------

    def get_statuses(self) -> list[tuple]:
        return self.__select("SELECT status_name FROM status")

    def get_status_id(self, name: str) -> int:
        res = self.__select(
            "SELECT status_id FROM status WHERE status_name=?", (name,)
        )
        return res[0][0] if res else None

    def get_skills(self) -> list[tuple]:
        return self.__select("SELECT * FROM skills")

    def get_projects(self, user_id: int) -> list[tuple]:
        return self.__select(
            "SELECT * FROM projects WHERE user_id=?",
            (user_id,)
        )

    def get_project_id(self, project_name: str, user_id: int) -> int:
        return self.__select(
            "SELECT project_id FROM projects WHERE project_name=? AND user_id=?",
            (project_name, user_id)
        )[0][0]

    def get_project_skills(self, project_name: str) -> str:
        rows = self.__select('''
            SELECT s.skill_name
            FROM project_skills ps
            JOIN skills s ON ps.skill_id=s.skill_id
            JOIN projects p ON ps.project_id=p.project_id
            WHERE p.project_name=?
        ''', (project_name,))
        return ", ".join(r[0] for r in rows)

    def get_project_photo(self, project_name: str, user_id: int) -> str | None:
        res = self.__select(
            "SELECT photo FROM projects WHERE project_name=? AND user_id=?",
            (project_name, user_id)
        )
        return res[0][0] if res and res[0][0] else None

    def get_project_info(self, user_id: int, project_name: str) -> list[tuple]:
        return self.__select('''
            SELECT p.project_name, p.description, p.url, s.status_name
            FROM projects p
            LEFT JOIN status s ON p.status_id=s.status_id
            WHERE p.user_id=? AND p.project_name=?
        ''', (user_id, project_name))
