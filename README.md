# Vocab Bot

A free Discord bot for learning SAT/GRE vocabulary. It teaches from about 1,700 SAT/GRE words, and `/define` can look up any English word. These are the commands:

- `/word` gives you a random word with its definition, an example sentence (when there is one), and how rare it is.
- `/define abate` looks up any English word. Press **Add to my flashcards** to study it.
- `/study` starts a flashcard session that only you can see. You see the word, press **Show answer**, then **Know it** or **Still learning**.
- `/lesson` is your daily lesson: 10 multiple-choice questions, only visible to you. Earn XP and keep your streak alive.
- `/progress` shows your streak, XP, and how many words you've studied and mastered.
- `/reminder 18` pings you in that channel at 6 PM if you haven't done a lesson yet that day. Use `/reminder` with no number to turn it off.

## Where the words come from

- `words.json` has 331 words with hand-written definitions and examples.
- `more_words.txt` has about 1,400 more SAT/GRE words, one per line, with no definitions.
- Definitions for those words, and for anything you `/define`, come from the [Free Dictionary API](https://dictionaryapi.dev). It's free and needs no account or key. Its definitions come from Wiktionary.
- Every word the bot downloads is saved in `word_cache.json`, so each word is only downloaded once.

### How the bot decides which words to teach

The bot uses the free [wordfreq](https://github.com/rspeer/wordfreq) library to score how common each word is in everyday English. It works offline.

- Words that are too common (as common as "benefit" or "cat") are never picked for lessons or flashcards. You can change this line in `dictionary.py`: `TOO_COMMON = 4.0`. A lower number skips more words.
- New words come in order from more common to rarer, so lessons start easier and get harder as you learn.
- Each word card shows its rarity from ★☆☆☆☆ (fairly common) to ★★★★★ (very rare).

Want more words? Add them to `more_words.txt`, one per line, and restart the bot. You don't need to write definitions.

## Lessons, XP, and streaks

Each lesson mixes words that are due for review with new words. Some questions show a definition and ask for the word, and others show a word and ask for its meaning.

- **+10 XP** for each right answer, plus **+20 XP** for finishing the lesson.
- Do at least one lesson a day to grow your 🔥 streak. Miss a whole day and it resets to 0.
- Lesson answers count toward your flashcard boxes too, so `/lesson` and `/study` work together.

Reminders and streaks use your computer's clock, and reminders only go out while the bot is running.

## How /study picks words

Every word you study goes into a box from 1 to 5. **Know it** moves the word up a box, and **Still learning** sends it back to box 1. The higher the box, the longer before you see the word again:

| Box | Comes back after |
|---|---|
| 1 | right away (10 minutes if you just missed it) |
| 2 | 1 day |
| 3 | 3 days |
| 4 | 1 week |
| 5 | 2 weeks (mastered!) |

Words that are due come first. When nothing is due, you get a new word. This is called spaced repetition, and it's how apps like Anki help you remember things long-term.

Your progress is saved in `progress.db` next to `bot.py`. Don't delete it unless you want to start over.

## Files

| File | What it is |
|---|---|
| `bot.py` | The bot itself |
| `progress.py` | Saves your flashcard progress |
| `dictionary.py` | Looks up words online and scores how rare they are |
| `words.json` | 331 words with hand-written definitions |
| `more_words.txt` | About 1,400 more words (definitions come from the dictionary) |
| `requirements.txt` | The Python libraries the bot needs |
| `.env.example` | A template for your secret settings |

## Setup (about 15 minutes, one time)

### 1. Install Python
Get Python 3.10 or newer from https://www.python.org/downloads/. On Windows, tick **"Add Python to PATH"** during install.

### 2. Create the bot on Discord
1. Go to https://discord.com/developers/applications and click **New Application**. Name it something like "Vocab Bot".
2. Open the **Bot** tab and click **Reset Token**, then **Copy**. This is your bot's password, so keep it secret.
3. Open the **OAuth2** tab, then **URL Generator**. Tick `bot` and `applications.commands`. Under Bot Permissions, tick **Send Messages** and **Embed Links**.
4. Copy the URL at the bottom, open it in your browser, and add the bot to your test server.

### 3. Get your server id
In Discord, open **User Settings → Advanced** and turn on **Developer Mode**. Then right-click your server's icon and choose **Copy Server ID**.

### 4. Add your settings
In the `vocab-bot` folder, make a copy of `.env.example` and name it `.env`. Open it and paste in your token and server id.

### 5. Install and run
Open a terminal in the `vocab-bot` folder and run:

```
pip install -r requirements.txt
python bot.py
```

(On Mac, use `pip3` and `python3`.) When you see `Logged in as Vocab Bot... words ready to learn.`, go to your server and type `/word`.

The bot only runs while that terminal window is open. Press `Ctrl+C` to stop it.

## Updating the bot
When there's new code, download the new files (or `git pull` if you cloned the repo), stop the bot with `Ctrl+C`, run `pip install -r requirements.txt` in case there's a new library, and run `python bot.py` again. Your `.env` and `progress.db` stay as they are.

## Adding words
The easy way: add the word to `more_words.txt` on its own line. The definition comes from the dictionary.

To write your own definition instead, open `words.json` and add an entry in the same format:

```json
{
  "word": "laconic",
  "part_of_speech": "adjective",
  "definition": "using very few words",
  "example": "His laconic reply was simply \"No.\""
}
```

Restart the bot to pick up the changes.

## Coming next
- **Step 4 (optional):** host the bot for free so it runs 24/7, and maybe build an iOS app with the same word list.
