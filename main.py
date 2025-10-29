import discord
from discord import app_commands
import aiohttp
import os

# Create bot instance with necessary intents
intents = discord.Intents.default()

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
    await interaction.response.send_message("👋 Hello! I'm your Discord bot, ready to send messages, GIFs, and images!")

# Command: Send a message
@bot.tree.command(name="message", description="Send a custom message")
@app_commands.describe(text="The message text to send")
async def send_message(interaction: discord.Interaction, text: str):
    """Send a custom text message"""
    await interaction.response.send_message(f"📝 {text}")

# Command: Send a GIF
@bot.tree.command(name="gif", description="Send a GIF")
@app_commands.describe(search="Search term for the GIF (e.g., 'funny cat', 'dance')")
async def send_gif(interaction: discord.Interaction, search: str = "random"):
    """Send a GIF using Tenor API"""
    await interaction.response.defer()
    
    tenor_key = os.getenv('TENOR_API_KEY')
    if not tenor_key:
        await interaction.followup.send("❌ GIF search is not configured. To enable this feature, add a TENOR_API_KEY to your secrets.\nGet a free API key at https://developers.google.com/tenor/guides/quickstart")
        return
    
    tenor_url = f"https://tenor.googleapis.com/v2/search?q={search}&key={tenor_key}&limit=1&random=true"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tenor_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        gif_url = data['results'][0]['media_formats']['gif']['url']
                        await interaction.followup.send(f"🎬 Here's a GIF for '{search}':\n{gif_url}")
                    else:
                        await interaction.followup.send(f"❌ No GIF found for '{search}'. Try another search term!")
                else:
                    await interaction.followup.send("❌ Failed to fetch GIF. Please try again.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching GIF: {str(e)}")

# Command: Send an image from URL
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

# Command: Send a random cat picture
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

# Command: Send a random dog picture
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

# Run the bot
if __name__ == "__main__":
    # Get token from environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please set your Discord bot token in the Secrets tab.")
        exit(1)
    
    bot.run(token)
