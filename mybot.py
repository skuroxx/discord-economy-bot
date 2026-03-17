import discord
from discord.ext import commands
import json
import random
import time
import os
from dotenv import load_dotenv

# ===== LOAD ENV =====
load_dotenv(dotenv_path=".env")
TOKEN = os.getenv("TOKEN")

# ===== CONFIG =====
DATA_FILE = "economy.json"
COOLDOWN = 900  # 15 min
PREFIX = "!"

SHOP = {
    "taxcard": {"price": 5000, "tax_reduce": 0.02},
    "premium": {"price": 15000, "tax_reduce": 0.05},
    "insurance": {"price": 8000, "steal_reduce": 0.3}
}

# ===== BOT =====
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ===== DATA =====
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "wallet": 0,
            "bank": 0,
            "tax_paid": 0,
            "inventory": [],
            "last_steal": 0
        }
    return data[user_id]

# ===== TAX REDUCTION =====
def get_tax_reduction(user):
    reduction = 0
    for item in user["inventory"]:
        if item in SHOP and "tax_reduce" in SHOP[item]:
            reduction += SHOP[item]["tax_reduce"]
    return reduction

# ===== ROLE SYSTEM =====
async def update_roles(member):
    user = get_user(member.id)
    total = user["wallet"] + user["bank"]

    roles_map = {
        5000: "Citizen",
        20000: "MP",
        50000: "CM",
        100000: "PM"
    }

    for amount, role_name in roles_map.items():
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role:
            if total >= amount and role not in member.roles:
                await member.add_roles(role)
            elif total < amount and role in member.roles:
                await member.remove_roles(role)

# ===== WELCOME SYSTEM =====
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel

    if not channel:
        return

    embed = discord.Embed(
        title="🪷 A New Member Has Arrived 🪷",
        description=f"""
✦ Welcome {member.mention} ✦  

➤ Enter to the server
➤ Follow the rules  
➤ Laude ne vhojyam

︵‿︵‿୨🪷୧‿︵‿︵
""",
        color=0xFFA500
    )

    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

    # 🎬 GIF HERE
    embed.set_image(url="https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyd2tjbWE5YXN0ZTdtZXJ3NmJ1aHJvcHhmdWhqMWtxeWx3bjRiZ2Y2ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/dvsQt2qh45tVl6YipK/giphy.gif")

    embed.set_footer(text="✦ bhen ke lode ✦")

    await channel.send(embed=embed)

# ===== EARN =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user = get_user(message.author.id)
    user["wallet"] += random.randint(5, 15)

    save_data(data)
    await bot.process_commands(message)

# ===== COMMANDS =====

@bot.command()
async def balance(ctx):
    user = get_user(ctx.author.id)

    embed = discord.Embed(
        title="💰 Balance",
        description=f"""
💸 Wallet: {user['wallet']}
🏦 Bank: {user['bank']}
🧾 Tax Paid: {user['tax_paid']}
""",
        color=0xFFA500
    )
    await ctx.send(embed=embed)

@bot.command()
async def deposit(ctx, amount: int):
    user = get_user(ctx.author.id)

    if amount > user["wallet"]:
        return await ctx.send("❌ Not enough money")

    reduction = get_tax_reduction(user)
    tax = int(amount * max(0, (0.12 - reduction))) if amount > 12000 else 0

    user["wallet"] -= amount
    user["bank"] += (amount - tax)
    user["tax_paid"] += tax

    save_data(data)
    await update_roles(ctx.author)

    await ctx.send(f"🏦 Deposited {amount} | Tax: {tax}")

@bot.command()
async def withdraw(ctx, amount: int):
    user = get_user(ctx.author.id)

    if amount > user["bank"]:
        return await ctx.send("❌ Not enough bank")

    user["bank"] -= amount
    user["wallet"] += amount

    save_data(data)
    await update_roles(ctx.author)

    await ctx.send(f"💸 Withdrawn {amount}")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender = get_user(ctx.author.id)
    receiver = get_user(member.id)

    if amount > sender["wallet"]:
        return await ctx.send("❌ Not enough money")

    reduction = get_tax_reduction(sender)
    tax = int(amount * max(0, (0.05 - reduction)))

    sender["wallet"] -= amount
    receiver["wallet"] += (amount - tax)
    sender["tax_paid"] += tax

    save_data(data)
    await update_roles(ctx.author)

    await ctx.send(f"💸 Sent {amount} to {member.mention} | Tax: {tax}")

@bot.command()
async def steal(ctx, member: discord.Member):
    thief = get_user(ctx.author.id)
    victim = get_user(member.id)

    now = time.time()
    if now - thief["last_steal"] < COOLDOWN:
        return await ctx.send("⏳ Cooldown active")

    if victim["wallet"] < 50:
        return await ctx.send("❌ Target too poor")

    reduction = 0
    if "insurance" in victim["inventory"]:
        reduction = SHOP["insurance"]["steal_reduce"]

    amount = int(random.randint(20, victim["wallet"] // 2) * (1 - reduction))

    victim["wallet"] -= amount
    thief["wallet"] += amount
    thief["last_steal"] = now

    save_data(data)
    await update_roles(ctx.author)

    await ctx.send(f"🕵️ Stole {amount} from {member.mention}")

@bot.command()
async def shop(ctx):
    text = ""
    for item, info in SHOP.items():
        text += f"{item} - 💰{info['price']}\n"

    embed = discord.Embed(title="🛒 Shop", description=text, color=0xFFA500)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    user = get_user(ctx.author.id)
    item = item.lower()

    if item not in SHOP:
        return await ctx.send("❌ Invalid item")

    if user["wallet"] < SHOP[item]["price"]:
        return await ctx.send("❌ Not enough money")

    user["wallet"] -= SHOP[item]["price"]
    user["inventory"].append(item)

    save_data(data)

    await ctx.send(f"✅ Bought {item}")

@bot.command()
async def leaderboard(ctx):
    sorted_users = sorted(data.items(), key=lambda x: x[1]["wallet"] + x[1]["bank"], reverse=True)

    text = ""
    for i, (uid, udata) in enumerate(sorted_users[:10], 1):
        total = udata["wallet"] + udata["bank"]
        text += f"{i}. <@{uid}> - {total}\n"

    embed = discord.Embed(title="🏆 Richest", description=text, color=0xFFA500)
    await ctx.send(embed=embed)

@bot.command()
async def taxleaderboard(ctx):
    sorted_users = sorted(data.items(), key=lambda x: x[1]["tax_paid"], reverse=True)

    text = ""
    for i, (uid, udata) in enumerate(sorted_users[:100], 1):
        text += f"{i}. <@{uid}> - {udata['tax_paid']}\n"

    embed = discord.Embed(title="🧾 Top Taxpayers", description=text, color=0xFFA500)
    await ctx.send(embed=embed)
    
@bot.command()
async def welcome(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title="🪷 A New Member Has Entered 🪷",
        description=f"""
✦ Welcome {member.mention} ✦  

➤ Enter to the server
➤ Follow the rules  
➤ Survive the system  

︵‿︵‿୨🪷୧‿︵‿︵
""",
        color=0xFFA500
    )

    embed.set_thumbnail(
        url=member.avatar.url if member.avatar else member.default_avatar.url
    )

    # 🎬 GIF (CHANGE THIS IF YOU WANT)
    embed.set_image(url="https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyd2tjbWE5YXN0ZTdtZXJ3NmJ1aHJvcHhmdWhqMWtxeWx3bjRiZ2Y2ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/dvsQt2qh45tVl6YipK/giphy.gif")

    embed.set_footer(text="✦ The Sinners Await ✦")

    await ctx.send(embed=embed)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"🔥 Bot online as {bot.user}")

bot.run(TOKEN)