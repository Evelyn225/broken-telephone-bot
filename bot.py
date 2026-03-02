import os
import random
import asyncio
import unicodedata
import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


_lang_pool_cache = None


def _is_latin(text: str) -> bool:
    return all(
        unicodedata.name(c, '').startswith('LATIN') or not c.isalpha()
        for c in text
    )


def get_language_pool():
    global _lang_pool_cache
    if _lang_pool_cache is not None:
        return _lang_pool_cache

    all_langs = GoogleTranslator(source='auto', target='en').get_supported_languages(as_dict=True)
    pool = []
    for name, code in all_langs.items():
        if 'english' in name.lower():
            continue
        try:
            sample = GoogleTranslator(source='en', target=code).translate('hello')
            if _is_latin(sample):
                pool.append(code)
        except Exception:
            continue

    _lang_pool_cache = pool
    print(f"[pool] {len(pool)} Latin-script languages loaded")
    return pool


def broken_telephone_sync(text: str, steps: int = 50) -> str:
    lang_pool = get_language_pool()
    chosen = random.sample(lang_pool, min(steps, len(lang_pool)))

    current = text
    for i, lang in enumerate(chosen, 1):
        try:
            current = GoogleTranslator(source='auto', target=lang).translate(current)
            print(f"[{i}/{steps}] {lang}: {current}")
        except Exception:
            print(f"[{i}/{steps}] {lang}: FAILED")
            continue

    try:
        current = GoogleTranslator(source='auto', target='en').translate(current)
        print(f"[final] en: {current}")
    except Exception:
        print("[final] en: FAILED")

    return current


@bot.tree.command(name="translate", description="Run the last message through multiple languages")
@app_commands.describe(steps="Number of translation steps (5–50, default 10)")
async def translate_cmd(interaction: discord.Interaction, steps: int = 10):
    if steps < 5 or steps > 50:
        await interaction.response.send_message("Steps must be between 5 and 50.", ephemeral=True)
        return

    await interaction.response.defer()

    last_msg = None
    async for msg in interaction.channel.history(limit=20):
        if not msg.author.bot:
            last_msg = msg
            break

    if last_msg is None:
        await interaction.followup.send("No messages found to translate.")
        return

    result = await asyncio.to_thread(broken_telephone_sync, last_msg.content, steps)

    if len(result) > 2000:
        result = result[:1997] + "..."

    await interaction.followup.send(result)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")
    await asyncio.to_thread(get_language_pool)
    print("[pool] Ready")


bot.run(TOKEN)
