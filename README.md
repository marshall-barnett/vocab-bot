# Vocab Bot

A free Discord bot for learning SAT/GRE vocabulary. This is **step 1**: a bot with 331 words and two commands.

- `/word` gives you a random word with its definition and an example sentence.
- `/define abate` looks up a specific word from the list.

## Files

| File | What it is |
|---|---|
| `bot.py` | The bot itself |
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
- **Step 2:** flashcards with "Know it" / "Still learning" buttons that remember your progress.
- **Step 3:** daily lessons, quizzes, XP, and streaks.
