# Vocab Bot

A free Discord bot for learning SAT/GRE vocabulary. Right now it has 331 words and these commands:

- `/word` gives you a random word with its definition and an example sentence.
- `/define abate` looks up a specific word from the list.
- `/study` starts a flashcard session that only you can see. You see the word, press **Show answer**, then **Know it** or **Still learning**.
- `/lesson` is your daily lesson: 10 multiple-choice questions, only visible to you. Earn XP and keep your streak alive.
- `/progress` shows your streak, XP, and how many words you've studied and mastered.
- `/reminder 18` pings you in that channel at 6 PM if you haven't done a lesson yet that day. Use `/reminder` with no number to turn it off.

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
| `words.json` | The word list (add your own words here!) |
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

(On Mac, use `pip3` and `python3`.) When you see `Logged in as Vocab Bot... 331 words loaded.`, go to your server and type `/word`.

The bot only runs while that terminal window is open. Press `Ctrl+C` to stop it.

## Updating the bot
When there's new code, download the new files (or `git pull` if you cloned the repo), stop the bot with `Ctrl+C`, and run `python bot.py` again. Your `.env` and `progress.db` stay as they are.

## Adding words
Open `words.json` and add an entry in the same format:

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
