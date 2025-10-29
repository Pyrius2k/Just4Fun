import discord
from discord import app_commands
import aiohttp
import os
import asyncio # Neu: Für den Spam-Befehl benötigt

# 1. Intents mit 'members' erweitern
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True # Für einige Funktionen hilfreich, sicherheitshalber belassen

class DiscordBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync commands with Discord
        await self.tree.sync()
        print("Commands synced!")

bot = DiscordBot()

@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user}!')
    print(f'Bot ID: {bot.user.id}')
    print('------')

# Command: Send a hello message
@bot.tree.command(name="hello", description="Send a friendly greeting message")
async def hello(interaction: discord.Interaction):
    """Send a hello message"""
    await interaction.response.send_message("👋 Hello! I'm your Discord bot, ready to send messages and images!")

# Command: Send a message
@bot.tree.command(name="message", description="Send a custom message")
@app_commands.describe(text="The message text to send")
async def send_message(interaction: discord.Interaction, text: str):
    """Send a custom text message"""
    await interaction.response.send_message(f"📝 {text}")

# --- Moderations-Befehle ---

# Command: Kick a member
@bot.tree.command(name="kick", description="Kicks a member from the server")
@app_commands.describe(member="The member to kick", reason="The reason for the kick")
@app_commands.default_permissions(kick_members=True) # Stellt sicher, dass nur Berechtigte den Befehl sehen/nutzen
async def kick_member(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
    """Kicks a member from the server (requires 'Kick Members' permission)"""
    
    # Der Bot muss in der Rollen-Hierarchie höher sein als das Ziel
    if interaction.guild.me.top_role <= member.top_role:
        await interaction.response.send_message(f"❌ Ich kann **{member.display_name}** nicht kicken, da deren Rolle höher oder gleich meiner eigenen ist.")
        return
    
    try:
        await member.kick(reason=f"Kick durch {interaction.user.name} | Grund: {reason}")
        await interaction.response.send_message(f"✅ **{member.display_name}** wurde gekickt. Grund: *{reason}*")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Ich habe nicht die notwendigen Berechtigungen, um dies zu tun. Bitte überprüfe meine Rollen.")

# Command: Ban a member
@bot.tree.command(name="ban", description="Bans a member from the server")
@app_commands.describe(member="The member to ban", reason="The reason for the ban")
@app_commands.default_permissions(ban_members=True) # Stellt sicher, dass nur Berechtigte den Befehl sehen/nutzen
async def ban_member(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
    """Bans a member from the server (requires 'Ban Members' permission)"""
    
    # Der Bot muss in der Rollen-Hierarchie höher sein als das Ziel
    if interaction.guild.me.top_role <= member.top_role:
        await interaction.response.send_message(f"❌ Ich kann **{member.display_name}** nicht bannen, da deren Rolle höher oder gleich meiner eigenen ist.")
        return
        
    try:
        await member.ban(reason=f"Ban durch {interaction.user.name} | Grund: {reason}")
        await interaction.response.send_message(f"✅ **{member.display_name}** wurde gebannt. Grund: *{reason}*")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Ich habe nicht die notwendigen Berechtigungen, um dies zu tun. Bitte überprüfe meine Rollen.")

# Command: Send a message multiple times (Spam)
@bot.tree.command(name="spam", description="Sends a message multiple times (max 20)")
@app_commands.describe(text="The message to spam", count="How many times (max 20)")
@app_commands.default_permissions(manage_messages=True) # Nur für Moderatoren
async def spam_message(interaction: discord.Interaction, text: str, count: app_commands.Range[int, 1, 20]):
    """Sends a message multiple times with a safety delay."""
    
    await interaction.response.send_message(f"💬 Spammen von '{text}' {count} Mal gestartet...")

    # Rate-Limit-Schutz: Begrenzen auf 20 und bauen eine Verzögerung ein
    for _ in range(count):
        await interaction.channel.send(text)
        await asyncio.sleep(1.0) # Warten Sie eine Sekunde zwischen jeder Nachricht

    await interaction.channel.send("✅ Spam-Befehl abgeschlossen.")


# Command: Send an image from URL (unverändert)
@bot.tree.command(name="image", description="Send an image from a URL")
@app_commands.describe(url="The image URL to send")
async def send_image(interaction: discord.Interaction, url: str):
    """Send an image from a URL"""
    # Create an embed with the image
    embed = discord.Embed(
        title="🖼️ Here's your image!",
        color=discord.Color.blue()
    )
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# Command: Send a random cat picture (unverändert)
@bot.tree.command(name="cat", description="Send a random cat picture")
async def send_cat(interaction: discord.Interaction):
    """Send a random cat picture from an API"""
    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search") as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        cat_url = data[0]['url']

                        embed = discord.Embed(
                            title="🐱 Random Cat!",
                            color=discord.Color.orange()
                        )
                        embed.set_image(url=cat_url)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ No cat picture available. Please try again.")
                else:
                    await interaction.followup.send("❌ Failed to fetch cat picture. Please try again.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching cat picture: {str(e)}")

# Command: Send a random dog picture (unverändert)
@bot.tree.command(name="dog", description="Send a random dog picture")
async def send_dog(interaction: discord.Interaction):
    """Send a random dog picture from an API"""
    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as response:
                if response.status == 200:
                    data = await response.json()
                    if data and data.get('message'):
                        dog_url = data['message']

                        embed = discord.Embed(
                            title="🐶 Random Dog!",
                            color=discord.Color.green()
                        )
                        embed.set_image(url=dog_url)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ No dog picture available. Please try again.")
                else:
                    await interaction.followup.send("❌ Failed to fetch dog picture. Please try again.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching dog picture: {str(e)}")

# Run the bot (unverändert)
if __name__ == "__main__":
    # Get token from environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please set your Discord bot token in the Secrets tab.")
        exit(1)
    
    bot.run(token)
