import discord
from discord import app_commands
import aiohttp
import os
import asyncio 
from flask import Flask
from threading import Thread
# NEU: Imports für Gemini
from google import genai
from google.genai import types

# --- Keep-Alive Funktion für Railway ---
def run_flask():
    app = Flask('')
    @app.route('/')
    def home():
        return "Bot is awake and hosted by Railway!"
    # Railway stellt den Port über eine Umgebungsvariable bereit
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Startet den Flask-Server in einem separaten Thread, um den Bot 24/7 online zu halten."""
    t = Thread(target=run_flask)
    t.start()
# --- Ende Keep-Alive Funktion ---


# --- Gemini API Initialisierung ---
try:
    gemini_client = genai.Client()
except Exception as e:
    print(f"❌ Gemini Client konnte nicht initialisiert werden (Prüfen Sie den Key): {e}")
    gemini_client = None

# Temporäre In-Memory Speicherung für Gemini Chats (Kontext pro Benutzer)
active_chats = {}

# 1. Intents setzen
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

class DiscordBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Synchronisiert Befehle beim Start (einmalig)
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
    await interaction.response.send_message("👋 Hello! I'm your Discord bot, ready to send messages and images!")

# Command: Send a message
@bot.tree.command(name="message", description="Send a custom message")
@app_commands.describe(text="The message text to send")
async def send_message(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"📝 {text}")

# --- Moderations-Befehle ---

# Command: Kick a member
@bot.tree.command(name="kick", description="Kicks a member from the server")
@app_commands.describe(member="The member to kick", reason="The reason for the kick")
@app_commands.default_permissions(kick_members=True)
async def kick_member(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
    await interaction.response.defer(ephemeral=True) 
    
    if interaction.guild.me.top_role <= member.top_role:
        await interaction.followup.send(f"❌ Ich kann **{member.display_name}** nicht kicken, da deren Rolle höher oder gleich meiner eigenen ist.")
        return
    
    try:
        await member.kick(reason=f"Kick durch {interaction.user.name} | Grund: {reason}")
        await interaction.followup.send(f"✅ **{member.display_name}** wurde gekickt. Grund: *{reason}*")
    except discord.Forbidden:
        await interaction.followup.send("❌ Ich habe nicht die notwendigen Berechtigungen, um dies zu tun. Bitte überprüfe meine Rollen.")

# Command: Ban a member
@bot.tree.command(name="ban", description="Bans a member from the server")
@app_commands.describe(member="The member to ban", reason="The reason for the ban")
@app_commands.default_permissions(ban_members=True)
async def ban_member(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
    await interaction.response.defer(ephemeral=True) 
    
    if interaction.guild.me.top_role <= member.top_role:
        await interaction.followup.send(f"❌ Ich kann **{member.display_name}** nicht bannen, da deren Rolle höher oder gleich meiner eigenen ist.")
        return
        
    try:
        await member.ban(reason=f"Ban durch {interaction.user.name} | Grund: {reason}")
        await interaction.followup.send(f"✅ **{member.display_name}** wurde gebannt. Grund: *{reason}*")
    except discord.Forbidden:
        await interaction.followup.send("❌ Ich habe nicht die notwendigen Berechtigungen, um dies zu tun. Bitte überprüfe meine Rollen.")

# Command: Send a message multiple times (Spam)
@bot.tree.command(name="spam", description="Sends a message multiple times (max 20)")
@app_commands.describe(text="The message to spam", count="How many times (max 20)")
@app_commands.default_permissions(manage_messages=True)
async def spam_message(interaction: discord.Interaction, text: str, count: app_commands.Range[int, 1, 20]):
    await interaction.response.send_message(f"💬 Spammen von '{text}' {count} Mal gestartet...", ephemeral=True) 

    for _ in range(count):
        await interaction.channel.send(text)
        await asyncio.sleep(1.0) 

    await interaction.channel.send("✅ Spam-Befehl abgeschlossen.")

# --- Gemini AI Befehl ---
@bot.tree.command(name="gemini", description="Ask Gemini a question or continue a conversation.")
@app_commands.describe(prompt="Your question or message to the AI")
async def gemini_chat(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer() 

    if not gemini_client:
        await interaction.followup.send("❌ Gemini-Chat ist nicht verfügbar. Bitte prüfen Sie den GEMINI_API_KEY.")
        return

    user_id = interaction.user.id
    
    if user_id not in active_chats:
        config = types.GenerateContentConfig(
            system_instruction="Du bist ein freundlicher, hilfreicher und humorvoller Discord-Bot namens AliBan. Halte deine Antworten kurz und prägnant."
        )
        
        active_chats[user_id] = gemini_client.chats.create(
            model='gemini-2.5-flash',
            config=config,
        )
        
    chat = active_chats[user_id]
    
    try:
        response = chat.send_message(prompt)
        ai_response = response.text if len(response.text) <= 2000 else response.text[:1950] + "..."

        embed = discord.Embed(
            title=f"🤖 Gemini-Antwort für {interaction.user.display_name}",
            description=ai_response,
            color=discord.Color.green()
        )
        embed.add_field(name="Ihre Frage:", value=f"*{prompt[:100]}...*" if len(prompt) > 100 else prompt, inline=False)
        embed.set_footer(text="Geben Sie /gemini erneut ein, um die Unterhaltung fortzusetzen.")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Fehler bei der Gemini-Anfrage: {str(e)}")
        # Optional: Lösche den Chat bei einem Fehler
        del active_chats[user_id]

# --- Media-Befehle ---

# Command: Send an image from URL
@bot.tree.command(name="image", description="Send an image from a URL")
@app_commands.describe(url="The image URL to send")
async def send_image(interaction: discord.Interaction, url: str):
    embed = discord.Embed(
        title="🖼️ Here's your image!",
        color=discord.Color.blue()
    )
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# Command: Send a GIF (Tenor API Key erforderlich!)
@bot.tree.command(name="gif", description="Send a GIF")
@app_commands.describe(search="Search term for the GIF (e.g., 'funny cat', 'dance')")
async def send_gif(interaction: discord.Interaction, search: str = "random"):
    await interaction.response.defer()

    tenor_key = os.getenv('TENOR_API_KEY')
    if not tenor_key:
        await interaction.followup.send("❌ GIF search ist nicht konfiguriert. Bitte fügen Sie einen TENOR_API_KEY in Railway hinzu.")
        return

    tenor_url = f"https://tenor.googleapis.com/v2/search?q={search}&key={tenor_key}&limit=1&random=true"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tenor_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        gif_url = data['results'][0]['media_formats']['gif']['url']
                        await interaction.followup.send(f"🎬 Hier ist ein GIF für '{search}':\n{gif_url}")
                    else:
                        await interaction.followup.send(f"❌ Kein GIF gefunden für '{search}'. Versuchen Sie einen anderen Suchbegriff!")
                else:
                    await interaction.followup.send("❌ Fehler beim Abrufen des GIF. Status: " + str(response.status))
    except Exception as e:
        await interaction.followup.send(f"❌ Fehler beim Abrufen des GIF: {str(e)}")


# Command: Send a random cat picture
@bot.tree.command(name="cat", description="Send a random cat picture")
async def send_cat(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search") as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        cat_url = data[0]['url']
                        embed = discord.Embed(title="🐱 Random Cat!", color=discord.Color.orange())
                        embed.set_image(url=cat_url)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ No cat picture available. Please try again.")
                else:
                    await interaction.followup.send("❌ Failed to fetch cat picture. Please try again.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching cat picture: {str(e)}")

# Command: Send a random dog picture
@bot.tree.command(name="dog", description="Send a random dog picture")
async def send_dog(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as response:
                if response.status == 200:
                    data = await response.json()
                    if data and data.get('message'):
                        dog_url = data['message']
                        embed = discord.Embed(title="🐶 Random Dog!", color=discord.Color.green())
                        embed.set_image(url=dog_url)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ No dog picture available. Please try again.")
                else:
                    await interaction.followup.send("❌ Failed to fetch dog picture. Please try again.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching dog picture: {str(e)}")

# --- TEMPORÄRER SYNCHRONISATIONS-BEFEHL ---
@bot.tree.command(name="sync", description="Syncs all global commands immediately (Owner only).")
async def sync_commands(interaction: discord.Interaction):
    # BITTE HIER IHRE EIGENE DISCORD BENUTZER-ID (als ganze Zahl) EINTRAGEN
    MEINE_BENUTZER_ID = IHRE_BENUTZER_ID_HIER
    
    if interaction.user.id != MEINE_BENUTZER_ID: 
        await interaction.response.send_message("❌ Nur der Bot-Besitzer kann diesen Befehl ausführen.", ephemeral=True)
        return

    await interaction.response.send_message("⚙️ Starte manuelle Synchronisation der Slash-Befehle...", ephemeral=True)
    await bot.tree.sync() 
    await interaction.followup.send("✅ Alle Befehle wurden erfolgreich synchronisiert!", ephemeral=True)
# --- ENDE DES TEMPORÄREN BEFEHLS ---


# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    
    # 2. Startet den Keep-Alive-Server im Hintergrund (Wichtig für Railway)
    keep_alive() 
    
    # 3. Startet den Discord-Bot
    bot.run(token)
