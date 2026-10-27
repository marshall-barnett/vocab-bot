# Vocab Bot - Step 1
# A Discord bot that teaches you SAT/GRE vocabulary words.
#
# Commands:
#   /word            -> shows a random vocab word
#   /define <word>   -> looks up a word from the list

import json
import os
import random

import discord
from discord import app_commands
from dotenv import load_dotenv

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


if __name__ == "__main__":
    if not TOKEN:
        print("No DISCORD_TOKEN found. Did you create your .env file? See README.md.")
    else:
        bot.run(TOKEN)
