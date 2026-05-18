import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data") / "ruins.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pattern_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL UNIQUE,
            representative_crop_path TEXT NOT NULL,
            representative_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS layouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            screenshot_path TEXT NOT NULL,
            top_crop_path TEXT NOT NULL,
            image_hash TEXT NOT NULL,
            stage_number TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (group_id) REFERENCES pattern_groups(id)
        )
        """
    )

    conn.commit()
    conn.close()


def add_pattern_group(group_name, representative_crop_path, representative_hash):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO pattern_groups (
            group_name,
            representative_crop_path,
            representative_hash,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            group_name.strip().lower(),
            representative_crop_path,
            str(representative_hash),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    group_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return group_id


def get_all_pattern_groups():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, group_name, representative_crop_path, representative_hash, created_at
        FROM pattern_groups
        ORDER BY id ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_next_group_name():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pattern_groups")
    count = cursor.fetchone()[0]

    conn.close()

    return f"top_pattern_{count + 1:03d}"


def add_layout(
    group_id,
    screenshot_path,
    top_crop_path,
    image_hash,
    stage_number="",
    notes="",
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO layouts (
            group_id,
            screenshot_path,
            top_crop_path,
            image_hash,
            stage_number,
            notes,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            group_id,
            screenshot_path,
            top_crop_path,
            str(image_hash),
            stage_number.strip(),
            notes.strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    conn.commit()
    conn.close()


def get_layouts_by_group(group_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            layouts.id,
            layouts.group_id,
            pattern_groups.group_name,
            layouts.screenshot_path,
            layouts.top_crop_path,
            layouts.image_hash,
            layouts.stage_number,
            layouts.notes,
            layouts.created_at
        FROM layouts
        JOIN pattern_groups ON layouts.group_id = pattern_groups.id
        WHERE layouts.group_id = ?
        ORDER BY layouts.id ASC
        """,
        (group_id,),
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_layouts():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            layouts.id,
            layouts.group_id,
            pattern_groups.group_name,
            layouts.screenshot_path,
            layouts.top_crop_path,
            layouts.image_hash,
            layouts.stage_number,
            layouts.notes,
            layouts.created_at
        FROM layouts
        JOIN pattern_groups ON layouts.group_id = pattern_groups.id
        ORDER BY layouts.id ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_layout(layout_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT screenshot_path, top_crop_path
        FROM layouts
        WHERE id = ?
        """,
        (layout_id,),
    )

    row = cursor.fetchone()

    cursor.execute(
        """
        DELETE FROM layouts
        WHERE id = ?
        """,
        (layout_id,),
    )

    conn.commit()
    conn.close()

    return row


def delete_pattern_group(group_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT representative_crop_path
        FROM pattern_groups
        WHERE id = ?
        """,
        (group_id,),
    )

    group_row = cursor.fetchone()

    cursor.execute(
        """
        SELECT screenshot_path, top_crop_path
        FROM layouts
        WHERE group_id = ?
        """,
        (group_id,),
    )

    layout_rows = cursor.fetchall()

    cursor.execute(
        """
        DELETE FROM layouts
        WHERE group_id = ?
        """,
        (group_id,),
    )

    cursor.execute(
        """
        DELETE FROM pattern_groups
        WHERE id = ?
        """,
        (group_id,),
    )

    conn.commit()
    conn.close()

    return group_row, layout_rows