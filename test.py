from javascript import require, On, Once, AsyncTask, once, off
from dotenv import load_dotenv
import os

mineflayer = require('mineflayer')

bot = mineflayer.createBot({
    "username": os.getenv("BOT_USERNAME"),
    "password": os.getenv("BOT_PASSWORD"),
    "host": os.getenv("TARGET_HOST"),
    "port": os.getenv("TARGET_PORT"),
    "version": os.getenv("TARGET_VERSION"),
    "hideErrors": False
})


@On(bot, "login")
def login(this):
    pass


@On(bot, 'chat')
def onChat(this, user, message, *rest):
    print(f'{user} said "{message}"')

    # If the message contains stop, remove the event listener and stop logging.
    if 'stop' in message:
        off(bot, 'chat', onChat)
