import discord
from discord.ext import commands
import asyncio
import json

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

with open("config.json") as f:
    config = json.load(f)

with open("ltcaddy.txt") as f:
    LTC_ADDRESS = f.read().strip()

with open("apikey.txt") as f:
    LTC_API_KEY = f.read().strip()

TOKEN = config["token"]
CATEGORY_ID = int(config["category_id"])

bot = commands.Bot(command_prefix=",", intents=intents)

role_data = {}

class ConfirmView(discord.ui.View):
    def __init__(self, buyer, seller):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.seller = seller

    @discord.ui.button(label="Confirm (10s)", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await asyncio.sleep(10)
        await interaction.response.edit_message(embed=discord.Embed(
            title="✅ Deal Confirmed",
            description=f"Funds are confirmed and released to {self.seller.mention}.",
            color=0x2ecc71
        ))

    @discord.ui.button(label="Return", style=discord.ButtonStyle.danger)
    async def return_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=discord.Embed(
            title="🔁 Return Process",
            description=f"{self.buyer.mention}, please send your **LTC address** here to receive the refund.",
            color=0xe74c3c
        ))
        def check(msg):
            return msg.author == self.buyer and msg.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", timeout=120.0, check=check)
            await interaction.channel.send(f"📥 LTC refund address received: `{msg.content}`")
        except asyncio.TimeoutError:
            await interaction.channel.send("⏰ Timeout. No LTC address received.")

class ConfirmRolesView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.success)
    async def correct_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        buyer = role_data[self.channel.id]["buyer"]
        seller = role_data[self.channel.id]["seller"]
        embed = discord.Embed(
            title="Release Confirmation",
            description=f"**Are you sure?**\n\nFunds will be sent to {seller.mention}. This action is final.",
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed, view=ConfirmView(buyer, seller))

    @discord.ui.button(label="Incorrect", style=discord.ButtonStyle.danger)
    async def incorrect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_role_embed(interaction.channel)

class RoleSelection(discord.ui.View):
    def __init__(self, message):
        super().__init__(timeout=None)
        self.message = message

    @discord.ui.button(label="Sending", style=discord.ButtonStyle.primary)
    async def sending_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cid = interaction.channel.id
        role_data.setdefault(cid, {"buyer": None, "seller": None, "message": self.message})
        role_data[cid]["buyer"] = interaction.user
        await self.update_message(interaction)

    @discord.ui.button(label="Receiving", style=discord.ButtonStyle.primary)
    async def receiving_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cid = interaction.channel.id
        role_data.setdefault(cid, {"buyer": None, "seller": None, "message": self.message})
        role_data[cid]["seller"] = interaction.user
        await self.update_message(interaction)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.delete()
        await send_role_embed(interaction.channel)

    async def update_message(self, interaction):
        cid = interaction.channel.id
        buyer = role_data[cid]["buyer"]
        seller = role_data[cid]["seller"]
        embed = discord.Embed(
            title="Role Selection",
            description="Select your role in the transaction:",
            color=0x5865F2
        )
        embed.add_field(name="Buyer (Sending LTC)", value=buyer.mention if buyer else "`None`", inline=False)
        embed.add_field(name="Seller (Receiving LTC)", value=seller.mention if seller else "`None`", inline=False)

        await self.message.edit(embed=embed, view=self)
        if buyer and seller:
            confirm_embed = discord.Embed(
                title="Is this Correct?",
                description=f"Receiving - {seller.mention}\nSending - {buyer.mention}",
                color=0x5865F2
            )
            await interaction.channel.send(embed=confirm_embed, view=ConfirmRolesView(interaction.channel))

async def send_role_embed(channel):
    embed = discord.Embed(
        title="Role Selection",
        description="Select your role in the transaction:",
        color=0x5865F2
    )
    embed.add_field(name="Buyer (Sending LTC)", value="`None`", inline=False)
    embed.add_field(name="Seller (Receiving LTC)", value="`None`", inline=False)

    message = await channel.send(embed=embed)
    await message.edit(view=RoleSelection(message))

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}!")
    await bot.tree.sync()

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == CATEGORY_ID:
        await asyncio.sleep(1)
        await send_role_embed(channel)

bot.run(TOKEN)
