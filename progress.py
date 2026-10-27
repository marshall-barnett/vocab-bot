# Saves each person's flashcard progress in a small database file (progress.db).
#
# How the "spaced repetition" works (called the Leitner box system):
#   Every word you study sits in a box from 1 to 5.
#   "Know it"        -> the word moves up one box and comes back later.
#   "Still learning" -> the word drops back to box 1 and comes back soon.
#   The higher the box, the longer the wait before you see it again.

import datetime
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

# New words are picked at random from the next 25 easiest words you haven't seen.
NEXT_UP = 25


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
    # One row per person: XP, streak, and reminder settings.
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
               user_id           INTEGER PRIMARY KEY,
               xp                INTEGER DEFAULT 0,
               streak            INTEGER DEFAULT 0,
               last_lesson_date  TEXT,
               remind_channel_id INTEGER,
               remind_hour       INTEGER,
               last_reminded     TEXT
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
    # all_words is sorted from most common to rarest, so you meet easier words first.
    new_words = [w for w in all_words if w not in seen]
    if new_words:
        return random.choice(new_words[:NEXT_UP])

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


def add_word(user_id, word):
    """Put a word you looked up into your flashcards (box 1, ready to study now)."""
    with connect() as db:
        added = db.execute(
            "INSERT OR IGNORE INTO cards (user_id, word, box, due_at) VALUES (?, ?, 1, ?)",
            (user_id, word, time.time()),
        ).rowcount
    return added == 1  # False if it was already in your flashcards


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


# ---------- Lessons, XP, and streaks ----------

def today():
    """Today's date as text, like "2026-10-27" (uses your computer's clock)."""
    return datetime.date.today().isoformat()


def pick_lesson_words(user_id, all_words, count=10):
    """Pick words for a lesson: words due for review first, then new words."""
    now = time.time()
    with connect() as db:
        due = [
            r[0]
            for r in db.execute(
                "SELECT word FROM cards WHERE user_id = ? AND due_at <= ? ORDER BY box, due_at",
                (user_id, now),
            )
        ]
        seen = {r[0] for r in db.execute("SELECT word FROM cards WHERE user_id = ?", (user_id,))}
    picked = due[:count]
    new_words = [w for w in all_words if w not in seen][:NEXT_UP]
    random.shuffle(new_words)
    picked += new_words[: count - len(picked)]

    # Still short (you've seen every word)? Fill up with random review words.
    if len(picked) < count:
        extra = [w for w in all_words if w not in picked]
        picked += random.sample(extra, min(count - len(picked), len(extra)))
    random.shuffle(picked)
    return picked


def get_user(user_id):
    """Get someone's XP, streak, and settings as a dictionary."""
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    user = dict(row)

    # If you missed a whole day, your streak is broken.
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if user["last_lesson_date"] not in (today(), yesterday):
        user["streak"] = 0
    return user


def finish_lesson(user_id, xp_earned):
    """Add XP and update the streak. Returns the new XP total and streak."""
    user = get_user(user_id)
    if user["last_lesson_date"] != today():
        user["streak"] += 1  # first lesson today keeps the streak going
    with connect() as db:
        db.execute(
            "UPDATE users SET xp = xp + ?, streak = ?, last_lesson_date = ? WHERE user_id = ?",
            (xp_earned, user["streak"], today(), user_id),
        )
    return user["xp"] + xp_earned, user["streak"]


# ---------- Daily reminders ----------

def set_reminder(user_id, channel_id, hour):
    """Turn on a daily reminder (hour is 0-23), or turn it off with hour=None."""
    get_user(user_id)  # make sure the person has a row
    with connect() as db:
        db.execute(
            "UPDATE users SET remind_channel_id = ?, remind_hour = ? WHERE user_id = ?",
            (channel_id, hour, user_id),
        )


def reminders_due(hour):
    """People who want a reminder at this hour and haven't done a lesson today."""
    with connect() as db:
        rows = db.execute(
            "SELECT user_id, remind_channel_id FROM users "
            "WHERE remind_hour = ? AND (last_lesson_date IS NULL OR last_lesson_date != ?) "
            "AND (last_reminded IS NULL OR last_reminded != ?)",
            (hour, today(), today()),
        ).fetchall()
    return rows


def mark_reminded(user_id):
    with connect() as db:
        db.execute("UPDATE users SET last_reminded = ? WHERE user_id = ?", (today(), user_id))
