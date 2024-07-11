import os
import dotenv

from javascript import require, On, Once, AsyncTask, once, off
from simple_chalk import chalk
import re

# Import required JavaScript libraries
mineflayer = require('mineflayer')
navigatePlugin = require('mineflayer-navigate')(mineflayer)
pathfinder = require('mineflayer-pathfinder')
Vec3 = require('vec3')

dotenv.load_dotenv()

# Bot configuration
BOT_USERNAME = os.getenv('BOT_USERNAME')
TARGET_VERSION = os.getenv('TARGET_VERSION')
SERVER_HOST = os.getenv("TARGET_HOST")
SERVER_PORT = os.getenv("TARGET_PORT")

print(f"{BOT_USERNAME}@{SERVER_HOST}:{SERVER_PORT}:{TARGET_VERSION}")


class PatrolBot:
    def __init__(self):
        print("Initializing patrolbot...")
        self.bot = mineflayer.createBot({
            'host': SERVER_HOST,
            'port': SERVER_PORT,
            'username': BOT_USERNAME,
            'hideErrors': False,
        })
        print("PatrolBot initialized.")

        self.bot.loadPlugin(pathfinder.pathfinder)
        navigatePlugin(self.bot)
        self.patrol_points = []
        self.is_patrolling = False
        self.current_patrol_index = 0

        self.setup_events()

    def setup_events(self):
        @On(self.bot, "login")
        def login(this):
            pass

        @On(self.bot, 'spawn')
        def handle_spawn(this):
            self.log("Bot spawned. Ready for commands!")
            self.bot.chat("hi")

        @On(self.bot, "kicked")
        def kicked(this, reason, loggedIn):
            if loggedIn:
                self.log(chalk.redBright(f"Kicked whilst trying to connect: {reason}"))

        @On(self.bot, 'whisper')
        def handle_chat(this, user: str, message: str, translate, jsonMsg, matches):
            parsedMessage = jsonMsg['json']['with'][1][''] if not (message is None) else message
            if user != self.bot.username and parsedMessage is not None:
                self.log(f"User {user} said message: {parsedMessage}")
                if parsedMessage.startswith('patrol '):
                    self.set_patrol_points(parsedMessage)
                elif parsedMessage == 'patrolStart':
                    self.start_patrol()
                elif parsedMessage == 'patrolStop':
                    self.stop_patrol()
                else:
                    self.log(f"Unknown message: {parsedMessage}")

        @On(self.bot, "end")
        def end(this, reason):
            self.log(chalk.red(f"Disconnected: {reason}"))

            # Turn off old events
            off(self.bot, "login", login)
            off(self.bot, "spawn", handle_spawn)
            off(self.bot, "kicked", kicked)
            off(self.bot, "chat", handle_chat)

            # Reconnect
            if self.reconnect:
                self.log(chalk.cyanBright(f"Attempting to reconnect"))
                self.start_bot()

            # Last event listener
            off(self.bot, "end", end)

    def set_patrol_points(self, message):
        points = re.findall(r'\(([-]?\d+),\s*([-]?\d+),\s*([-]?\d+)\)', message)
        self.patrol_points = [Vec3(int(x), int(y), int(z)) for x, y, z in points]
        self.log(f"Patrol points set: {self.patrol_points}")

    def start_patrol(self):
        if not self.patrol_points:
            self.log("No patrol points set. Use 'patrol (x,y,z) ...' to set points.")
            self.bot.chat("No patrol points set.")
            return

        self.is_patrolling = True
        self.current_patrol_index = 0
        self.log("Starting patrol...")
        self.move_to_next_point()

    def stop_patrol(self):
        self.is_patrolling = False
        self.bot.navigate.stop()
        self.log("Stopping patrol.")

    def move_to_next_point(self):
        if not self.is_patrolling:
            return

        goal = self.patrol_points[self.current_patrol_index]
        self.log(f"Moving to point: {goal}")

        try:
            # self.log(self.bot.players['Type32__'].entity.position)
            # self.bot.pathfinder.setGoal(pathfinder.pathfinder.goals.GoalNear(goal.x, goal.y, goal.z, 1))
            self.bot.navigate.to(goal)
        except Exception as e:
            self.log(f"Failed to move point: {goal}")
            self.stop_patrol()

        # @On(self.bot, 'goal_reached')
        # def handle_goal_reached(this, *rest):
        #     off(self.bot, 'goal_reached', handle_goal_reached)
        #     self.log(f"Reached point: {goal}")
        #     self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
        #     self.move_to_next_point()

        @On(self.bot.navigate, 'arrived')
        def handle_goal_arrived(this):
            off(self.bot.navigate, 'arrived', handle_goal_arrived)
            self.log(f"Reached point: {goal}")
            self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            self.move_to_next_point()

    def log(self, message):
        print(chalk.blue(f"[{self.bot.username}] {message}"))


# Create and start the bot
patrol_bot = PatrolBot()
