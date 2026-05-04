"""Repository for knowledge bank data — experiences, skills, achievements, education, projects."""

import sqlite3


# Whitelisted column names per table — prevents SQL injection via dynamic column names
# Whitelisted columns derived from actual DB schema (PRAGMA table_info)
ALLOWED_COLUMNS = {
    "experiences": {"type", "title", "company", "start_date", "end_date", "description", "metadata", "profile_id"},
    "skills": {"name", "category", "proficiency", "source_experience_id", "profile_id"},
    "education": {"institution", "degree", "field", "start_date", "end_date", "metadata"},
    "projects": {"name", "description", "tech_stack", "url", "metadata"},
}


def _validate_column_names(table_name: str, field_names: set[str]) -> None:
    """Reject any field name not in the whitelist for this table."""
    allowed = ALLOWED_COLUMNS.get(table_name, set())
    invalid_columns = field_names - allowed
    if invalid_columns:
        raise ValueError(f"Invalid column names for {table_name}: {invalid_columns}")


class KnowledgeRepository:
    """CRUD operations for the knowledge bank."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # --- Experiences ---

    def save_experience(
        self,
        type: str,
        title: str,
        company: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        description: str | None = None,
        metadata: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO experiences (type, title, company, start_date, end_date, description, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (type, title, company, start_date, end_date, description, metadata),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_experience(self, experience_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM experiences WHERE id = ?", (experience_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_experiences(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM experiences ORDER BY start_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_experience(self, experience_id: int, **fields) -> None:
        if not fields:
            return
        _validate_column_names("experiences", set(fields.keys()))
        set_clause = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [experience_id]
        self._conn.execute(
            f"UPDATE experiences SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        self._conn.commit()

    def delete_experience(self, experience_id: int) -> None:
        self._conn.execute("DELETE FROM experiences WHERE id = ?", (experience_id,))
        self._conn.commit()

    # --- Skills ---

    def save_skill(
        self,
        name: str,
        category: str,
        proficiency: str | None = None,
        source_experience_id: int | None = None,
    ) -> int | None:
        # Check for existing skill with same name (case-insensitive)
        existing = self._conn.execute(
            "SELECT id FROM skills WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        if existing:
            return None

        cursor = self._conn.execute(
            """INSERT INTO skills (name, category, proficiency, source_experience_id)
               VALUES (?, ?, ?, ?)""",
            (name, category, proficiency, source_experience_id),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_skills(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM skills ORDER BY category, name").fetchall()
        return [dict(r) for r in rows]

    def delete_skill(self, skill_id: int) -> None:
        """Delete a single skill by ID."""
        self._conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        self._conn.commit()

    def delete_skills_by_category(self, category: str) -> int:
        """Delete all skills in a category. Returns count deleted."""
        cursor = self._conn.execute("DELETE FROM skills WHERE category = ?", (category,))
        self._conn.commit()
        return cursor.rowcount

    def update_skill(self, skill_id: int, **fields: str) -> None:
        """Update a skill's name and/or category."""
        _validate_column_names("skills", set(fields.keys()))
        updates = {key: value for key, value in fields.items() if value is not None}
        if not updates:
            return
        set_clause = ", ".join(f"{field_name} = ?" for field_name in updates)
        values = list(updates.values()) + [skill_id]
        self._conn.execute(f"UPDATE skills SET {set_clause} WHERE id = ?", values)
        self._conn.commit()

    # --- Achievements ---

    def save_achievement(
        self,
        experience_id: int,
        description: str,
        metric: str | None = None,
        impact: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO achievements (experience_id, description, metric, impact)
               VALUES (?, ?, ?, ?)""",
            (experience_id, description, metric, impact),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_achievements(self, experience_id: int | None = None) -> list[dict]:
        if experience_id is not None:
            rows = self._conn.execute(
                "SELECT * FROM achievements WHERE experience_id = ?", (experience_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM achievements").fetchall()
        return [dict(r) for r in rows]

    # --- Education ---

    def save_education(
        self,
        institution: str,
        degree: str | None = None,
        field: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO education (institution, degree, field, start_date, end_date)
               VALUES (?, ?, ?, ?, ?)""",
            (institution, degree, field, start_date, end_date),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_education(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM education").fetchall()
        return [dict(r) for r in rows]

    def delete_education(self, education_id: int) -> None:
        self._conn.execute("DELETE FROM education WHERE id = ?", (education_id,))
        self._conn.commit()

    def update_education(self, education_id: int, **fields: str) -> None:
        """Update an education entry's fields."""
        _validate_column_names("education", set(fields.keys()))
        updates = {key: value for key, value in fields.items() if value is not None}
        if not updates:
            return
        set_clause = ", ".join(f"{field_name} = ?" for field_name in updates)
        values = list(updates.values()) + [education_id]
        self._conn.execute(f"UPDATE education SET {set_clause} WHERE id = ?", values)
        self._conn.commit()

    # --- Projects ---

    def save_project(
        self,
        name: str,
        description: str | None = None,
        tech_stack: str | None = None,
        url: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO projects (name, description, tech_stack, url)
               VALUES (?, ?, ?, ?)""",
            (name, description, tech_stack, url),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_projects(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM projects").fetchall()
        return [dict(r) for r in rows]

    def delete_project(self, project_id: int) -> None:
        self._conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self._conn.commit()

    def update_project(self, project_id: int, **fields: str) -> None:
        """Update a project's fields."""
        _validate_column_names("projects", set(fields.keys()))
        updates = {key: value for key, value in fields.items() if value is not None}
        if not updates:
            return
        set_clause = ", ".join(f"{field_name} = ?" for field_name in updates)
        values = list(updates.values()) + [project_id]
        self._conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        self._conn.commit()

    # --- Aggregate ---

    def get_full_knowledge_bank(self) -> dict:
        """Return the entire knowledge bank as a dict of lists."""
        return {
            "experiences": self.list_experiences(),
            "skills": self.list_skills(),
            "achievements": self.list_achievements(),
            "education": self.list_education(),
            "projects": self.list_projects(),
        }
