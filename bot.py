import discord
from discord.ext import tasks
import requests
import re
import os

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")  # Token stored as environment variable
CHANNEL_ID = 1472699067124678819

DOC_URL = "https://docs.google.com/document/d/1FS8dcbHAkd70VmSBHiivXxE0Isj6dn2p7jyKugY91ro/export?format=txt"

CHECK_INTERVAL = 30  # seconds between checks

# =========================
# DISCORD SETUP
# =========================

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

last_header_sent = None  # tracks last sent header

# Header = line containing 2 or more links
HEADER_PATTERN = r'(https?://\S+\s+){2,}'

# =========================
# FUNCTIONS
# =========================

def get_new_messages():
    global last_header_sent

    try:
        response = requests.get(DOC_URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching document: {e}")
        return []

    lines = response.text.strip().split("\n")

    messages = []
    current_message = []
    current_header = None

    for line in lines:
        if re.search(HEADER_PATTERN, line):
            # If we already collected a message, save it
            if current_message and current_header != last_header_sent:
                messages.append((current_header, "\n".join(current_message)))

            current_header = line.strip()
            current_message = [line.strip()]
        else:
            if current_message:
                current_message.append(line.strip())

    # Add last message
    if current_message and current_header != last_header_sent:
        messages.append((current_header, "\n".join(current_message)))

    if messages:
        last_header_sent = messages[-1][0]

    # Return only message content
    return [msg[1] for msg in messages]


@tasks.loop(seconds=CHECK_INTERVAL)
async def check_google_doc():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("Channel not found.")
        return

    new_messages = get_new_messages()

    for msg in new_messages:
        # Split long messages (Discord limit = 2000 characters)
        for i in range(0, len(msg), 2000):
            await channel.send(msg[i:i+2000])

        print("New message sent.\n")


@client.event
async def on_ready():
    print(f"Bot connected as {client.user}")
    check_google_doc.start()


# =========================
# RUN BOT
# =========================

if not TOKEN:
    print("ERROR: TOKEN environment variable not set.")
else:
    client.run(TOKEN)
