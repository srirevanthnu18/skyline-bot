import discord
from discord.ext import commands
import random
import json
import os
import asyncio
import time
import threading
import io
import tarfile
import requests
import imageio_ffmpeg
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TOKEN_2 = os.getenv("DISCORD_TOKEN_2")
TOKEN_3 = os.getenv("DISCORD_TOKEN_3")
TOKEN_4 = os.getenv("DISCORD_TOKEN_4")
TOKEN_5 = os.getenv("DISCORD_TOKEN_5")
TOKEN_6 = os.getenv("DISCORD_TOKEN_6")
TOKEN_7 = os.getenv("DISCORD_TOKEN_7")
TOKEN_8 = os.getenv("DISCORD_TOKEN_8")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ffmpeg (bundled via imageio-ffmpeg, no install needed) ---
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
print(f"ffmpeg path: {FFMPEG_PATH}")

# --- libopus (download from Ubuntu package without root) ---
def extract_libopus(dest_path):
    url = "http://archive.ubuntu.com/ubuntu/pool/main/o/opus/libopus0_1.3.1-0ubuntu1_amd64.deb"
    print("Downloading libopus package...")
    data = requests.get(url, timeout=60).content
    pos = 8  # skip "!<arch>\n"
    while pos < len(data):
        name = data[pos:pos+16].decode(errors="ignore").strip()
        size = int(data[pos+48:pos+58].decode(errors="ignore").strip())
        content = data[pos+60:pos+60+size]
        pos = pos + 60 + size + (size % 2)
        if name.startswith("data.tar"):
            with tarfile.open(fileobj=io.BytesIO(content)) as tar:
                for member in tar.getmembers():
                    if "libopus.so" in member.name and not member.islnk():
                        f = tar.extractfile(member)
                        if f:
                            with open(dest_path, "wb") as out:
                                out.write(f.read())
                            print(f"libopus extracted to {dest_path}")
                            return True
    return False

LIBOPUS_PATH = os.path.join(SCRIPT_DIR, "libopus.so.0")
if not discord.opus.is_loaded():
    for lib in ["libopus.so.0", "libopus.so", "libopus"]:
        try:
            discord.opus.load_opus(lib)
            print(f"Loaded opus: {lib}")
            break
        except:
            pass
    if not discord.opus.is_loaded():
        if not os.path.exists(LIBOPUS_PATH):
            extract_libopus(LIBOPUS_PATH)
        try:
            discord.opus.load_opus(LIBOPUS_PATH)
            print("Loaded bundled libopus")
        except Exception as e:
            print(f"WARNING: Could not load libopus: {e}")

# --- audio file ---
AUDIO_URL = "https://github.com/srirevanthnu18/skyline-bot/releases/download/v1.0/audio.wav"
AUDIO_FILE = os.path.join(SCRIPT_DIR, "audio.wav")

if not os.path.exists(AUDIO_FILE):
    print(f"Downloading audio.wav...")
    try:
        r = requests.get(AUDIO_URL, stream=True, timeout=180)
        r.raise_for_status()
        with open(AUDIO_FILE, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Download complete. Size: {os.path.getsize(AUDIO_FILE)} bytes")
    except Exception as e:
        print(f"ERROR: Could not download audio.wav: {e}")
else:
    print(f"audio.wav exists ({os.path.getsize(AUDIO_FILE)} bytes)")


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

# --- Bot factory ---
def make_bot(bot_name="SKYLINE"):
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="sky ", intents=intents, help_command=None)
    spam_tracker = {}
    # Stagger delay: SKYLINE-1 = 0s, SKYLINE-2 = 0.7s, SKYLINE-3 = 1.4s, etc.
    try:
        bot_index = int(bot_name.split("-")[-1]) - 1
    except (ValueError, IndexError):
        bot_index = 0
    stagger_delay = bot_index * 0.7

    @bot.event
    async def on_ready():
        print(f"{bot_name} Online as {bot.user} in {len(bot.guilds)} server(s)")
        # Global sync — makes user-installed commands work in DMs and any server
        try:
            await bot.tree.sync()
            print(f"[{bot_name}] Global slash commands synced")
        except Exception as e:
            print(f"[{bot_name}] Global sync error: {e}")
        # Per-guild sync for instant availability
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
            except Exception as e:
                print(f"[{bot_name}] Sync error in {guild.name}: {e}")

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

    @bot.tree.command(name="skyjoin", description="Make the bot join your current voice channel")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    async def skyjoin(interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        target_channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        try:
            if vc is None:
                await target_channel.connect()
            else:
                await vc.move_to(target_channel)
            await interaction.followup.send(f"✅ Joined **{target_channel.name}**!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)

    @bot.tree.command(name="skyplay", description="Play the default audio in the voice channel")
    async def play(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            vc = interaction.guild.voice_client
            if vc is None:
                if interaction.user.voice:
                    vc = await interaction.user.voice.channel.connect()
                    await asyncio.sleep(1)
                else:
                    await interaction.followup.send("❌ Join a voice channel first or I need to already be in one!")
                    return
            if not vc.is_connected():
                await interaction.followup.send("❌ Not connected to voice. Try again in a moment.")
                return
            if vc.is_playing():
                vc.stop()
            source = discord.FFmpegPCMAudio(AUDIO_FILE, executable=FFMPEG_PATH, options="-ac 2")
            vc.play(discord.PCMVolumeTransformer(source, volume=2.0))
            print(f"[{bot_name}] Playing audio for {interaction.user}")
            await interaction.followup.send("🎵 Playing audio!")
        except Exception as e:
            print(f"[{bot_name}] Play error: {type(e).__name__}: {e}")
            await interaction.followup.send(f"❌ Error: `{type(e).__name__}: {e}`")

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.bot:
            return

        guild = member.guild
        # Use system channel for join/leave messages, fallback to first text channel
        text_channel = guild.system_channel or next(
            (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None
        )

        joined_vc = before.channel is None and after.channel is not None
        switched_vc = before.channel is not None and after.channel is not None and before.channel != after.channel
        left_vc = before.channel is not None and after.channel is None

        if joined_vc:
            if text_channel:
                await text_channel.send(f"vakkam da mama! 🔥 {member.mention}")

        if joined_vc or switched_vc:
            await asyncio.sleep(stagger_delay)
            vc = guild.voice_client
            target_channel = after.channel
            try:
                if vc is None:
                    vc = await target_channel.connect()
                    await asyncio.sleep(1)
                elif vc.channel != target_channel:
                    await vc.move_to(target_channel)
                    await asyncio.sleep(1)
                # Retry up to 3 times if not connected yet
                for attempt in range(3):
                    if vc.is_connected():
                        break
                    await asyncio.sleep(1)
                if vc.is_connected() and not vc.is_playing() and os.path.exists(AUDIO_FILE):
                    source = discord.FFmpegPCMAudio(AUDIO_FILE, executable=FFMPEG_PATH, options="-ac 2")
                    vc.play(discord.PCMVolumeTransformer(source, volume=2.0))
                    print(f"[{bot_name}] Playing audio in {target_channel.name} ({guild.name})")
                else:
                    print(f"[{bot_name}] Skipped play: connected={vc.is_connected() if vc else False}")
            except Exception as e:
                print(f"[{bot_name}] Auto-join/play error: {e}")

        if left_vc and text_channel:
            await text_channel.send(f"dei mama poriya ? 😢 {member.mention}")

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

    @bot.tree.command(name="skytype", description="Send a message multiple times")
    @discord.app_commands.describe(message="The message to send", times="How many times to send it")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def skytype(interaction: discord.Interaction, message: str, times: int):
        if times < 1:
            await interaction.response.send_message("❌ Times must be at least 1.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Sending your message {times} time(s)!", ephemeral=True)
        for _ in range(times):
            await interaction.followup.send(message)
            await asyncio.sleep(0.5)

    @bot.command()
    async def help(ctx):
        embed = discord.Embed(
            title="SKYLINE Help Panel",
            description="Here's what I can do:",
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

    return bot

# --- Keepalive server ---
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SKYLINE is alive!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    print(f"Keepalive server on port {port}")
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- Run both bots ---
async def main():
    instances = []
    coros = []
    for name, token in [("SKYLINE-1", TOKEN), ("SKYLINE-2", TOKEN_2), ("SKYLINE-3", TOKEN_3), ("SKYLINE-4", TOKEN_4), ("SKYLINE-5", TOKEN_5), ("SKYLINE-6", TOKEN_6), ("SKYLINE-7", TOKEN_7), ("SKYLINE-8", TOKEN_8)]:
        if token:
            b = make_bot(name)
            instances.append(b)
            coros.append(b.start(token))
    if not coros:
        print("ERROR: No tokens found. Set DISCORD_TOKEN, DISCORD_TOKEN_2, or DISCORD_TOKEN_3.")
        return
    await asyncio.gather(*coros)

asyncio.run(main())
