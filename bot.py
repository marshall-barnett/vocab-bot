# Vocab Bot - Step 2
# A Discord bot that teaches you SAT/GRE vocabulary words.
#
# Commands:
#   /word            -> shows a random vocab word
#   /define <word>   -> looks up a word from the list
#   /study           -> flashcards that remember which words you know
#   /progress        -> see how many words you've learned

import json
import os
import random

import discord
from discord import app_commands
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


@bot.tree.command(name="progress", description="See how many words you've learned")
async def show_progress(interaction: discord.Interaction):
    boxes, due = progress.get_stats(interaction.user.id)
    studied = sum(boxes.values())
    mastered = boxes[5]
    lines = [
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
