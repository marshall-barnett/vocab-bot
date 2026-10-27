# Vocab Bot - Step 3
# A Discord bot that teaches you SAT/GRE vocabulary words.
#
# Commands:
#   /word            -> shows a random vocab word
#   /define <word>   -> looks up a word from the list
#   /study           -> flashcards that remember which words you know
#   /lesson          -> today's lesson: 10 quiz questions, earn XP and keep your streak
#   /progress        -> see your XP, streak, and how many words you've learned
#   /reminder        -> get pinged if you haven't done a lesson by a certain hour

import datetime
import json
import os
import random

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

import progress

# Load the secret bot token (and your server id) from the .env file.
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # your test server's id, so commands show up instantly

# Load the word list. Each word looks like:
# {"word": "...", "part_of_speech": "...", "definition": "...", "example": "..."}
WORDS_FILE = os.path.join(os.path.dirname(__file__), "words.json")
with open(WORDS_FILE, encoding="utf-8") as f:
    WORDS = json.load(f)

# A dictionary so we can find a word quickly by its name.
WORDS_BY_NAME = {w["word"].lower(): w for w in WORDS}


def make_word_card(w):
    """Turn a word into a nice-looking Discord embed (the colored box)."""
    card = discord.Embed(
        title=w["word"],
        description=f"*{w['part_of_speech']}*\n\n{w['definition']}",
        color=discord.Color.blurple(),
    )
    card.add_field(name="Example", value=w["example"], inline=False)
    return card


def make_card_front(w):
    """The front of a flashcard: just the word, so you can guess the meaning."""
    return discord.Embed(
        title=w["word"],
        description=f"*{w['part_of_speech']}*\n\nDo you know what this means?",
        color=discord.Color.gold(),
    )


class CardFront(discord.ui.View):
    """Buttons under the front of a flashcard."""

    def __init__(self, user_id, word_name):
        super().__init__(timeout=600)  # buttons stop working after 10 minutes
        self.user_id = user_id
        self.word_name = word_name

    @discord.ui.button(label="Show answer", style=discord.ButtonStyle.primary)
    async def show_answer(self, interaction: discord.Interaction, button: discord.ui.Button):
        w = WORDS_BY_NAME[self.word_name.lower()]
        await interaction.response.edit_message(
            embed=make_word_card(w), view=CardBack(self.user_id, self.word_name)
        )

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.secondary)
    async def stop_studying(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Nice session! Type `/study` any time to keep going.", embed=None, view=None
        )


class CardBack(discord.ui.View):
    """Buttons under the back of a flashcard (after you see the answer)."""

    def __init__(self, user_id, word_name):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.word_name = word_name

    @discord.ui.button(label="Know it", emoji="✅", style=discord.ButtonStyle.success)
    async def know_it(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer(interaction, knew_it=True)

    @discord.ui.button(label="Still learning", emoji="🔁", style=discord.ButtonStyle.danger)
    async def still_learning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer(interaction, knew_it=False)

    async def answer(self, interaction, knew_it):
        box = progress.record_answer(self.user_id, self.word_name, knew_it)
        if knew_it:
            note = f"Moved **{self.word_name}** up to box {box} of 5."
        else:
            note = f"No problem, **{self.word_name}** will come back soon."
        await show_next_card(interaction, note)


async def show_next_card(interaction, note=None):
    """Show the front of the next flashcard (or say you're all caught up)."""
    user_id = interaction.user.id
    word_name = progress.pick_word(user_id, [w["word"] for w in WORDS])
    if word_name is None:
        content = (note + "\n\n" if note else "") + (
            "🎉 You're all caught up! No words are due right now. Come back later."
        )
        embed, view = None, None
    else:
        content = note
        embed = make_card_front(WORDS_BY_NAME[word_name.lower()])
        view = CardFront(user_id, word_name)

    if interaction.type == discord.InteractionType.application_command:
        # Typed /study: send a new private message.
        await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=True)
    else:
        # Clicked a button: swap the card in the same message.
        await interaction.response.edit_message(content=content, embed=embed, view=view)


# ---------- Lessons (the Duolingo part) ----------

XP_PER_CORRECT = 10
XP_LESSON_BONUS = 20  # for finishing the whole lesson
LETTERS = ["A", "B", "C", "D"]


def make_question(word_name, number, total):
    """Build one multiple-choice question about a word.

    Half the time you get a definition and pick the word.
    The other half you get a word and pick the definition.
    Returns the question card and the index (0-3) of the right answer.
    """
    w = WORDS_BY_NAME[word_name.lower()]
    wrong = random.sample([x for x in WORDS if x is not w], 3)
    choices = wrong + [w]
    random.shuffle(choices)
    answer = choices.index(w)

    if random.random() < 0.5:
        prompt = f"Which word means:\n> {w['definition']}"
        options = [c["word"] for c in choices]
    else:
        prompt = f"What does **{w['word']}** mean?"
        options = [c["definition"] for c in choices]

    lines = [prompt, ""] + [f"**{LETTERS[i]}.** {opt}" for i, opt in enumerate(options)]
    card = discord.Embed(
        title=f"Question {number} of {total}",
        description="\n".join(lines),
        color=discord.Color.orange(),
    )
    return card, answer


class Lesson(discord.ui.View):
    """Keeps track of one lesson: which question you're on and how many you got right."""

    def __init__(self, user_id, word_names):
        super().__init__(timeout=1800)  # 30 minutes to finish
        self.user_id = user_id
        self.word_names = word_names
        self.number = 0
        self.correct = 0
        self.card, self.answer = make_question(word_names[0], 1, len(word_names))
        for i, letter in enumerate(LETTERS):
            button = discord.ui.Button(label=letter, style=discord.ButtonStyle.primary)
            button.callback = self.make_callback(i)
            self.add_item(button)

    def make_callback(self, choice):
        async def callback(interaction: discord.Interaction):
            await self.check_answer(interaction, choice)
        return callback

    async def check_answer(self, interaction, choice):
        word_name = self.word_names[self.number]
        w = WORDS_BY_NAME[word_name.lower()]
        right = choice == self.answer
        progress.record_answer(self.user_id, word_name, right)

        if right:
            self.correct += 1
            feedback = f"✅ Correct! **{w['word']}**: {w['definition']} (+{XP_PER_CORRECT} XP)"
        else:
            feedback = (
                f"❌ The answer was **{LETTERS[self.answer]}**. "
                f"**{w['word']}**: {w['definition']}\n*{w['example']}*"
            )

        self.number += 1
        if self.number < len(self.word_names):
            self.card, self.answer = make_question(
                self.word_names[self.number], self.number + 1, len(self.word_names)
            )
            await interaction.response.edit_message(content=feedback, embed=self.card, view=self)
        else:
            await self.finish(interaction, feedback)

    async def finish(self, interaction, feedback):
        self.stop()
        xp_earned = self.correct * XP_PER_CORRECT + XP_LESSON_BONUS
        total_xp, streak = progress.finish_lesson(self.user_id, xp_earned)
        summary = discord.Embed(
            title="🎉 Lesson complete!",
            description=(
                f"You got **{self.correct} of {len(self.word_names)}** right.\n\n"
                f"**+{xp_earned} XP** (total: {total_xp} XP)\n"
                f"🔥 **{streak}-day streak**"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(content=feedback, embed=summary, view=None)


@tasks.loop(minutes=1)
async def send_reminders():
    """Every minute, check if anyone needs their daily reminder (at most once a day)."""
    now = datetime.datetime.now()
    for user_id, channel_id in progress.reminders_due(now.hour):
        channel = bot.get_channel(channel_id)
        if channel is not None:
            await channel.send(
                f"<@{user_id}> 📚 Time for today's vocab lesson! Type `/lesson` to keep your streak going."
            )
        progress.mark_reminded(user_id)


@send_reminders.before_loop
async def before_reminders():
    await bot.wait_until_ready()  # wait until the bot is logged in


class VocabBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        # The "tree" holds all of our slash commands.
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Tell Discord about our slash commands.
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)  # instant in your server
        else:
            await self.tree.sync()  # works everywhere, but can take up to an hour
        send_reminders.start()

    async def on_ready(self):
        print(f"Logged in as {self.user}. {len(WORDS)} words loaded.")


bot = VocabBot()


@bot.tree.command(name="word", description="Get a random SAT/GRE vocab word")
async def word(interaction: discord.Interaction):
    w = random.choice(WORDS)
    await interaction.response.send_message(embed=make_word_card(w))


@bot.tree.command(name="define", description="Look up a word from the vocab list")
@app_commands.describe(word="The word to look up")
async def define(interaction: discord.Interaction, word: str):
    w = WORDS_BY_NAME.get(word.lower().strip())
    if w is None:
        await interaction.response.send_message(
            f"Sorry, **{word}** isn't in the word list yet.", ephemeral=True
        )
    else:
        await interaction.response.send_message(embed=make_word_card(w))


@bot.tree.command(name="study", description="Study flashcards (only you can see them)")
async def study(interaction: discord.Interaction):
    await show_next_card(interaction)


@bot.tree.command(name="lesson", description="Today's lesson: 10 quiz questions (only you can see it)")
async def lesson(interaction: discord.Interaction):
    word_names = progress.pick_lesson_words(interaction.user.id, [w["word"] for w in WORDS])
    view = Lesson(interaction.user.id, word_names)
    await interaction.response.send_message(embed=view.card, view=view, ephemeral=True)


@bot.tree.command(name="reminder", description="Get a ping if you haven't done a lesson by a certain hour")
@app_commands.describe(hour="Hour of the day, 0-23 (for example 18 means 6 PM). Leave empty to turn off.")
async def reminder(interaction: discord.Interaction, hour: app_commands.Range[int, 0, 23] = None):
    progress.set_reminder(interaction.user.id, interaction.channel_id, hour)
    if hour is None:
        message = "Reminders are off."
    else:
        message = (
            f"Got it! If you haven't done `/lesson` by **{hour}:00**, I'll ping you in this channel."
        )
    await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="progress", description="See your XP, streak, and words learned")
async def show_progress(interaction: discord.Interaction):
    boxes, due = progress.get_stats(interaction.user.id)
    user = progress.get_user(interaction.user.id)
    studied = sum(boxes.values())
    mastered = boxes[5]
    lessoned_today = user["last_lesson_date"] == progress.today()
    lines = [
        f"🔥 **Streak:** {user['streak']} day(s)" + ("" if lessoned_today else " (do `/lesson` today!)"),
        f"⭐ **XP:** {user['xp']}",
        f"**Words studied:** {studied} of {len(WORDS)}",
        f"**Mastered (box 5):** {mastered}",
        f"**Due for review now:** {due}",
        "",
    ]
    for box, count in boxes.items():
        bar = "🟩" * min(count, 20)
        lines.append(f"Box {box}: {count} {bar}")
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s progress",
        description="\n".join(lines),
        color=discord.Color.green(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        print("No DISCORD_TOKEN found. Did you create your .env file? See README.md.")
    else:
        bot.run(TOKEN)
