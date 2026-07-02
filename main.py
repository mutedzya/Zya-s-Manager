import discord
from discord import app_commands
from discord.ext import commands
import re

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Simple in-memory storage for server configurations
# (In a production bot, you'd use a database like SQLite)
server_configs = {}

# List of banned words for basic automod
HATE_SPEECH_WORDS = ["badword1", "badword2"] # Replace with actual words to filter

@bot.event
async def on_ready():
    print(f'{bot.user.name} is now online!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# --- CONFIGURATION COMMANDS (Admin Only) ---

@bot.tree.command(name="setup_welcomer", description="Set the channel for welcome messages.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_welcomer(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id
    if guild_id not in server_configs:
        server_configs[guild_id] = {}
    server_configs[guild_id]['welcome_channel'] = channel.id
    await interaction.response.send_message(f"Welcome channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="setup_news", description="Set the channel for server news/milestones.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_news(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id
    if guild_id not in server_configs:
        server_configs[guild_id] = {}
    server_configs[guild_id]['news_channel'] = channel.id
    await interaction.response.send_message(f"News channel set to {channel.mention}", ephemeral=True)

# Error handling for unauthorized users trying to use admin commands
@setup_welcomer.error
@setup_news.error
async def admin_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)

# --- MODERATION COMMANDS ---

@bot.tree.command(name="warn", description="Warn a member.")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    # In a full bot, you'd save this to a database. For now, we DM the user and log it.
    try:
        await member.send(f"You have been warned in {interaction.guild.name} for: {reason}")
    except discord.Forbidden:
        pass # User has DMs closed
    await interaction.response.send_message(f"{member.mention} has been warned for: {reason}")

# --- AUTOMOD & FILE FILTERING EVENTS ---

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    guild_id = message.guild.id

    # 1. Automod: Check for hate speech / banned words
    if any(word in message.content.lower() for word in HATE_SPEECH_WORDS):
        await message.delete()
        try:
            # Timeout for 10 minutes (600 seconds)
            import datetime
            duration = datetime.timedelta(minutes=10)
            await message.author.timeout(duration, reason="Hate speech detected by AutoMod")
            await message.channel.send(f"{message.author.mention} has been timed out for 10 minutes for foul language.", delete_after=10)
        except discord.Forbidden:
            await message.channel.send("Failed to timeout user due to missing permissions.", delete_after=5)
        return

    # 2. File Filter: Delete non-img attachments if attachments exist
    if message.attachments:
        for attachment in message.attachments:
            filename = attachment.filename.lower()
            if not (filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg')):
                await message.delete()
                await message.channel.send(f"{message.author.mention}, only PNG and JPG/JPEG files are allowed in this channel!", delete_after=5)
                break 

# --- WELCOMER & SERVER NEWS EVENTS ---

@bot.event
async def on_member_join(member):
    guild = member.guild
    guild_id = guild.id
    
    # Welcomer Message
    if guild_id in server_configs and 'welcome_channel' in server_configs[guild_id]:
        channel = bot.get_channel(server_configs[guild_id]['welcome_channel'])
        if channel:
            await channel.send(f"Welcome to the server, {member.mention}! 🎉")

    # Milestone News (Every 10 members as an example)
    member_count = guild.member_count
    if member_count % 10 == 0: # Triggers at 10, 20, 50, 100, etc.
        if guild_id in server_configs and 'news_channel' in server_configs[guild_id]:
            channel = bot.get_channel(server_configs[guild_id]['news_channel'])
            if channel:
                await channel.send(f"🎉 **Milestone Reached!** We now have **{member_count}** members! 🎉")

@bot.event
async def on_guild_channel_update(before, after):
    # Detect boosts by tracking premium subscription count changes
    if before.guild.premium_subscription_count < after.guild.premium_subscription_count:
        guild_id = after.guild.id
        if guild_id in server_configs and 'news_channel' in server_configs[guild_id]:
            channel = bot.get_channel(server_configs[guild_id]['news_channel'])
            if channel:
                await channel.send(f"🚀 **Server Boosted!** Thank you for boosting the server! Current level: {after.guild.premium_tier}")

# Run the bot (Replace 'YOUR_BOT_TOKEN' with your actual token)
bot.run('YOUR_BOT_TOKEN')
