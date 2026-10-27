# Looks up any English word in the Free Dictionary API (https://dictionaryapi.dev),
# and scores how common a word is with the wordfreq library.
#
# The Free Dictionary API is free and needs no account or key. Its definitions
# come from Wiktionary.
#
# Every word we look up is saved in word_cache.json, so each word is only
# downloaded once. Words you've already seen keep working even without internet.

import asyncio
import json
import os
import re
import urllib.parse

import aiohttp  # comes with discord.py, so there's nothing extra to install
from wordfreq import zipf_frequency

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "word_cache.json")

# Give up on the dictionary after 2.5 seconds (Discord wants an answer within 3).
TIMEOUT = aiohttp.ClientTimeout(total=2.5)

# How common a word is, on a scale from about 0 to 8 (the "Zipf" scale):
#   7 = "the", 5 = "happy", 4.8 = "cat", 3.4 = "ubiquitous", 2.4 = "laconic", 1.4 = "pulchritude"
# Words at or above this number are too common to be worth quizzing you on.
TOO_COMMON = 4.0


def how_common(word):
    """How common a word is in everyday English (higher = more common)."""
    return zipf_frequency(word, "en")


def worth_learning(word):
    """True if a word is rare enough to be a good vocab word."""
    return how_common(word) < TOO_COMMON


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


# word -> card (a dictionary like the ones in words.json),
# or None if the dictionary doesn't have that word.
CACHE = load_cache()


def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, indent=1, ensure_ascii=False)


def tidy(text):
    """Make API definitions look like ours: "Using few words." -> "using few words"."""
    text = text.strip().rstrip(".")
    if len(text) > 1 and not text[1].isupper():  # leave things like "NASA" alone
        text = text[0].lower() + text[1:]
    return text


def make_card(word, data):
    """Turn the API's answer into a card shaped like the ones in words.json."""
    for entry in data:
        for meaning in entry.get("meanings", []):
            definitions = meaning.get("definitions", [])
            if not definitions:
                continue
            # Use the first definition, and the first example sentence we can find.
            examples = [d["example"] for d in definitions if d.get("example")]
            return {
                "word": word,
                "part_of_speech": meaning.get("partOfSpeech", ""),
                "definition": tidy(definitions[0]["definition"]),
                "example": examples[0] if examples else "",
                "source": "dictionaryapi.dev",
            }
    return None


def is_missing(word):
    """True if we already asked the dictionary and it doesn't have this word."""
    word = word.lower().strip()
    return word in CACHE and CACHE[word] is None


async def lookup(word):
    """Get a word's card from the dictionary. Returns None if it can't be found."""
    word = word.lower().strip()
    if word in CACHE:
        return CACHE[word]
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(API_URL.format(urllib.parse.quote(word))) as reply:
                if reply.status == 404:
                    card = None  # the dictionary doesn't know this word
                elif reply.status != 200:
                    return None  # something went wrong; try again another time
                else:
                    card = make_card(word, await reply.json())
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None  # no internet, or the dictionary is down; try again another time
    CACHE[word] = card
    save_cache()
    return card


def cached_cards():
    """Every word we've downloaded so far (used for wrong answers in quizzes)."""
    return [card for card in CACHE.values() if card]


def hide_word(word, text):
    """Blank out the word in its own definition, so quizzes don't give it away."""
    return re.sub(re.escape(word), "____", text, flags=re.IGNORECASE)


def rarity_stars(word):
    """1 to 5 stars: how rare (and how impressive) a word is."""
    common = how_common(word)
    stars = 1 + sum(common < cutoff for cutoff in (3.5, 3.0, 2.5, 2.0))
    return "★" * stars + "☆" * (5 - stars)
