import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio
from quart import Quart

# 1. Setup a tiny background web server for Render to ping
app = Quart(__name__)

@app.route('/')
async def home():
    return "Zya's Manager is alive!"

async def run_webserver():
    # Render provides a 'PORT' environment variable automatically
    import os
    port = int(os.environ.get("PORT", 8080))
    await app.run_task(host="0.0.0.0", port=port)

# 2. Setup your Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
server_configs = {}
HATE_SPEECH_WORDS = ["badword1", "badword2"] 

@bot.event
async def on_ready():
    print(f'{bot.user.name} is now online!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

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

@setup_welcomer.error
@setup_news.error
async def admin_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need Administrator permissions to use this command.", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a member.")
@app_commands.checks.has_permissions(administrator=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    try:
        await member.send(f"You have been warned in {interaction.guild.name} for: {reason}")
    except discord.Forbidden:
        pass
    await interaction.response.send_message(f"{member.mention} has been warned for: {reason}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    guild_id = message.guild.id
    if any(word in message.content.lower() for word in HATE_SPEECH_WORDS):
        await message.delete()
        try:
            duration = datetime.timedelta(minutes=10)
            await message.author.timeout(duration, reason="Hate speech detected by AutoMod")
            await message.channel.send(f"{message.author.mention} has been timed out for 10 minutes.", delete_after=10)
        except discord.Forbidden:
            pass
        return
    if message.attachments:
        for attachment in message.attachments:
            filename = attachment.filename.lower()
            if not (filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg')):
                await message.delete()
                await message.channel.send(f"{message.author.mention}, only PNG and JPG/JPEG files are allowed!", delete_after=5)
                break 

@bot.event
async def on_member_join(member):
    guild = member.guild
    guild_id = guild.id
    if guild_id in server_configs and 'welcome_channel' in server_configs[guild_id]:
        channel = bot.get_channel(server_configs[guild_id]['welcome_channel'])
        if channel:
            await channel.send(f"Welcome to the server, {member.mention}! 🎉")
    member_count = guild.member_count
    if member_count % 10 == 0:
        if guild_id in server_configs and 'news_channel' in server_configs[guild_id]:
            channel = bot.get_channel(server_configs[guild_id]['news_channel'])
            if channel:
                await channel.send(f"🎉 **Milestone Reached!** We now have **{member_count}** members! 🎉")

@bot.event
async def on_guild_channel_update(before, after):
    if before.guild.premium_subscription_count < after.guild.premium_subscription_count:
        guild_id = after.guild.id
        if guild_id in server_configs and 'news_channel' in server_configs[guild_id]:
            channel = bot.get_channel(server_configs[guild_id]['news_channel'])
            if channel:
                await channel.send(f"🚀 **Server Boosted!** Current level: {after.guild.premium_tier}")

# 3. Start both the web server and the bot together
async def main():
    import os
    # Fetch token securely from Render environment variables
    token = os.environ.get("YOUR_BOT_TOKEN") 
    await asyncio.gather(
        run_webserver(),
        bot.start(token)
    )

if __name__ == "__main__":
    asyncio.run(main())
