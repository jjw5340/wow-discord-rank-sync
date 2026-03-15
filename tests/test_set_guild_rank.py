import os

from dotenv import load_dotenv

from src.bot import DISCORD_BOT_TOKEN, client, set_guild_rank

load_dotenv()

TEST_USER_ID = os.getenv("TEST_USER_ID")
TEST_RANK = "Veteran"


@client.event
async def on_ready():
    print(f"Bot connected as {client.user}")

    await set_guild_rank(TEST_USER_ID, TEST_RANK)

    print("Test role assignment complete")

    await client.close()


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
