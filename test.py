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