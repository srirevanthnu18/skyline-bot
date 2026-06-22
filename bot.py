import discord
from discord.ext import commands
import random
import json
import os
import asyncio
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

AUDIO_URL = "https://files.catbox.moe/bgnql2.wav"

if not os.path.exists("audio.wav"):
    print("Downloading audio.wav...")
    try:
        r = requests.get(AUDIO_URL, stream=True, timeout=120)
        r.raise_for_status()
        with open("audio.wav", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
    except Exception as e:
        print(f"Warning: Could not download audio.wav: {e}")

GUILD_ID = 1446877712001138800
VOICE_CHANNEL_ID = 1470723472513699924
VC_TEXT_CHANNEL_ID = 1470723472513699924

if not discord.opus.is_loaded():
    try:
        discord.opus.load_opus("libopus")
    except:
        discord.opus.load_opus("libopus.so.0")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="sky ", intents=intents, help_command=None)

if not os.path.exists("levels.json"):
    with open("levels.json", "w") as f:
        json.dump({}, f)

if not os.path.exists("warnings.json"):
    with open("warnings.json", "w") as f:
        json.dump({}, f)

def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

AUDIO_FILE = "audio.wav"

@bot.event
async def on_ready():
    print(f"SKYLINE Online as {bot.user}")
    guild_obj = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild_obj)
    await bot.tree.sync(guild=guild_obj)
    guild = bot.get_guild(GUILD_ID)
    if guild:
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel:
            try:
                if guild.voice_client is None:
                    await channel.connect()
            except:
                pass

@bot.command()
@commands.has_permissions(administrator=True)
async def join(ctx, channel_id: int):
    channel = ctx.guild.get_channel(channel_id)
    if channel is None or not isinstance(channel, discord.VoiceChannel):
        await ctx.send("❌ Invalid voice channel ID.")
        return
    vc = ctx.guild.voice_client
    if vc is None:
        await channel.connect()
    else:
        await vc.move_to(channel)
    await ctx.send(f"✅ Joined **{channel.name}**!")

@bot.tree.command(name="skyplay", description="Play the default audio in the voice channel")
async def play(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        vc = interaction.guild.voice_client

        if vc is None:
            if interaction.user.voice:
                vc = await interaction.user.voice.channel.connect()
            else:
                await interaction.followup.send("❌ Join a voice channel first or I need to already be in one!")
                return

        if vc.is_playing():
            vc.stop()

        source = discord.FFmpegPCMAudio(AUDIO_FILE, options="-ac 2")
        vc.play(discord.PCMVolumeTransformer(source, volume=1.0))
        print(f"Playing audio for {interaction.user}")
        await interaction.followup.send("🎵 Playing audio!")
    except Exception as e:
        print(f"Play error: {type(e).__name__}: {e}")
        await interaction.followup.send(f"❌ Error: `{type(e).__name__}: {e}`")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        if member.id == bot.user.id and after.channel is None:
            await asyncio.sleep(5)
            guild = bot.get_guild(GUILD_ID)
            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if channel:
                await channel.connect()
        return

    guild = bot.get_guild(GUILD_ID)
    text_channel = guild.get_channel(VC_TEXT_CHANNEL_ID) if guild else None

    joined_vc = before.channel is None and after.channel is not None
    switched_vc = before.channel is not None and after.channel is not None and before.channel != after.channel
    left_vc = before.channel is not None and after.channel is None

    if joined_vc:
        if text_channel:
            await text_channel.send(f"vakkam da mama! 🔥 {member.mention}")

    if joined_vc or switched_vc:
        vc = member.guild.voice_client
        target_channel = after.channel
        try:
            if vc is None:
                vc = await target_channel.connect()
            elif vc.channel != target_channel:
                await vc.move_to(target_channel)
            if not vc.is_playing() and os.path.exists(AUDIO_FILE):
                source = discord.FFmpegPCMAudio(AUDIO_FILE, options="-ac 2")
                vc.play(discord.PCMVolumeTransformer(source, volume=1.0))
        except Exception as e:
            print(f"Auto-join/play error: {e}")

    if left_vc and text_channel:
        await text_channel.send(f"dei mama poriya ? 😢 {member.mention}")

spam_tracker = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        content = message.content
        for part in content.split():
            if part.lower().startswith("/sky"):
                rest = content[content.lower().find("/sky") + len("/sky"):].strip()
                if rest.lower().startswith("join"):
                    args = rest.split()
                    if len(args) >= 2:
                        try:
                            channel_id = int(args[1])
                            channel = message.guild.get_channel(channel_id)
                            if channel is None or not isinstance(channel, discord.VoiceChannel):
                                await message.channel.send("❌ Invalid voice channel ID.")
                            else:
                                vc = message.guild.voice_client
                                if vc is None:
                                    await channel.connect()
                                else:
                                    await vc.move_to(channel)
                                await message.channel.send(f"✅ Joined **{channel.name}**!")
                        except ValueError:
                            await message.channel.send("❌ Please provide a valid channel ID.")
                    else:
                        await message.channel.send("❌ Usage: @bot /sky join <channelid>")
                break

    user_id = message.author.id
    current_time = time.time()

    if user_id not in spam_tracker:
        spam_tracker[user_id] = []

    spam_tracker[user_id].append(current_time)
    spam_tracker[user_id] = [
        t for t in spam_tracker[user_id] if current_time - t < 5
    ]

    if len(spam_tracker[user_id]) > 5:
        await message.channel.send(f"{message.author.mention} stop spamming ⚠")
        return

    data = load_json("levels.json")
    uid = str(user_id)

    if uid not in data:
        data[uid] = {"xp": 0, "level": 1, "last_message": 0}

    if current_time - data[uid]["last_message"] > 60:
        data[uid]["xp"] += 5
        data[uid]["last_message"] = current_time

        xp = data[uid]["xp"]
        new_level = int((xp / 100) ** 0.5)

        if new_level > data[uid]["level"]:
            data[uid]["level"] = new_level
            await message.channel.send(
                f"{message.author.mention} leveled up to Level {new_level}!"
            )

        save_json("levels.json", data)

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Only Administrators can use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required argument.")
    else:
        pass

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="SKYLINE Help Panel",
        description="Here’s what I can do:",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Moderation (Admin Only)",
        value="`sky kick @user`\n`sky ban @user`\n`sky warn @user`\n`sky mute @user 10`",
        inline=False
    )

    embed.add_field(
        name="Fun Commands",
        value="`sky rps rock`\n`sky roll`",
        inline=False
    )

    embed.add_field(
        name="Level System",
        value="`sky level`\n`sky daily`",
        inline=False
    )

    embed.add_field(
        name="Voice System",
        value="Auto VC Lock Enabled",
        inline=False
    )

    embed.set_footer(text="SKYLINE • Server Core System")
    await ctx.send(embed=embed)

@bot.command()
async def level(ctx):
    data = load_json("levels.json")
    uid = str(ctx.author.id)

    if uid in data:
        await ctx.send(f"Level: {data[uid]['level']} | XP: {data[uid]['xp']}")
    else:
        await ctx.send("No XP yet.")

@bot.command()
async def daily(ctx):
    data = load_json("levels.json")
    uid = str(ctx.author.id)

    if uid not in data:
        data[uid] = {"xp": 0, "level": 1, "last_message": 0}

    data[uid]["xp"] += 50
    save_json("levels.json", data)

    await ctx.send("Daily reward claimed (+50 XP)")

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"{member} kicked.")

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"{member} banned.")

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    warnings = load_json("warnings.json")
    uid = str(member.id)

    if uid not in warnings:
        warnings[uid] = []

    warnings[uid].append(reason)
    save_json("warnings.json", warnings)

    await ctx.send(f"{member} warned.")

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, minutes: int):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")

    await member.add_roles(muted_role)
    await ctx.send(f"{member} muted for {minutes} minutes.")

    await asyncio.sleep(minutes * 60)
    await member.remove_roles(muted_role)

@bot.command()
async def rps(ctx, choice):
    options = ["rock", "paper", "scissors"]
    choice = choice.lower()

    if choice not in options:
        await ctx.send("Use: sky rps rock/paper/scissors")
        return

    bot_choice = random.choice(options)

    if choice == bot_choice:
        result = "It's a tie!"
    elif (
        (choice == "rock" and bot_choice == "scissors") or
        (choice == "paper" and bot_choice == "rock") or
        (choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win!"
    else:
        result = "You lose!"

    await ctx.send(f"I chose {bot_choice}. {result}")

@bot.command()
async def roll(ctx):
    await ctx.send(f"You rolled {random.randint(1,6)}")

bot.run(TOKEN)
