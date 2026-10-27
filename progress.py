# Saves each person's flashcard progress in a small database file (progress.db).
#
# How the "spaced repetition" works (called the Leitner box system):
#   Every word you study sits in a box from 1 to 5.
#   "Know it"        -> the word moves up one box and comes back later.
#   "Still learning" -> the word drops back to box 1 and comes back soon.
#   The higher the box, the longer the wait before you see it again.

import os
import random
import sqlite3
import time

DB_FILE = os.path.join(os.path.dirname(__file__), "progress.db")

# How long to wait (in days) before showing a word again, for each box.
BOX_WAIT_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}

# A word in box 1 that you just missed comes back after 10 minutes, not instantly.
RETRY_SECONDS = 10 * 60

SECONDS_PER_DAY = 24 * 60 * 60


def connect():
    db = sqlite3.connect(DB_FILE)
    db.execute(
        """CREATE TABLE IF NOT EXISTS cards (
               user_id  INTEGER,
               word     TEXT,
               box      INTEGER,
               due_at   REAL,
               PRIMARY KEY (user_id, word)
           )"""
    )
    return db


def pick_word(user_id, all_words):
    """Choose the next word to study: a word that's due for review, or a new one."""
    now = time.time()
    with connect() as db:
        # 1. A word you've seen before that's ready for review (lowest box first).
        row = db.execute(
            "SELECT word FROM cards WHERE user_id = ? AND due_at <= ? "
            "ORDER BY box, due_at LIMIT 1",
            (user_id, now),
        ).fetchone()
        if row:
            return row[0]

        # 2. Otherwise, a brand new word you haven't studied yet.
        seen = {r[0] for r in db.execute("SELECT word FROM cards WHERE user_id = ?", (user_id,))}
    new_words = [w for w in all_words if w not in seen]
    if new_words:
        return random.choice(new_words)

    # 3. You've studied every word and nothing is due. Nice!
    return None


def record_answer(user_id, word, knew_it):
    """Move the word to a new box based on your answer, and set when it's due next."""
    now = time.time()
    with connect() as db:
        row = db.execute(
            "SELECT box FROM cards WHERE user_id = ? AND word = ?", (user_id, word)
        ).fetchone()
        box = row[0] if row else 1

        if knew_it:
            box = min(box + 1, 5)
            due_at = now + BOX_WAIT_DAYS[box] * SECONDS_PER_DAY
        else:
            box = 1
            due_at = now + RETRY_SECONDS

        db.execute(
            "INSERT OR REPLACE INTO cards (user_id, word, box, due_at) VALUES (?, ?, ?, ?)",
            (user_id, word, box, due_at),
        )
    return box


def get_stats(user_id):
    """Count how many of your words are in each box, plus how many are due right now."""
    with connect() as db:
        counts = dict(
            db.execute(
                "SELECT box, COUNT(*) FROM cards WHERE user_id = ? GROUP BY box", (user_id,)
            ).fetchall()
        )
        due = db.execute(
            "SELECT COUNT(*) FROM cards WHERE user_id = ? AND due_at <= ?",
            (user_id, time.time()),
        ).fetchone()[0]
    return {box: counts.get(box, 0) for box in range(1, 6)}, due
