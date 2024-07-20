import os
import dotenv
import jwt

from javascript import require, On, Once, AsyncTask, once, off
from simple_chalk import chalk
import re
from cccommands import CommandParser, CommandBuilder

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
USAGE_WHITELIST = os.getenv('USAGE_WHITELIST')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

whitelist: list[str] = USAGE_WHITELIST.split(',')

print(f"{BOT_USERNAME}@{SERVER_HOST}:{SERVER_PORT}:{TARGET_VERSION}")

cmd_parser = CommandParser()
cmd_parser.register_command(
    CommandBuilder("patrol")
        .add_subcommand(CommandBuilder("set", Vec3, continued_params=True))
        .add_subcommand(CommandBuilder("get"))
        .add_subcommand(CommandBuilder("start"))
        .add_subcommand(CommandBuilder("stop"))
)
cmd_parser.register_command(
    CommandBuilder("overseer")
        .add_subcommand(CommandBuilder("bind"))
        .add_subcommand(CommandBuilder("unbind"))
        .add_subcommand(CommandBuilder("report"))
        .add_subcommand(CommandBuilder("receive", str))
)


class OverseerBot:
    def __init__(self):
        print("Initialized Base Class Bot.")

    def from_jwt(self, token: str):
        try:
            decoded_payload = jwt.decode(token, ENCRYPTION_KEY, algorithms=["HS256"])
            return decoded_payload['command']
            # print(f"Decoded payload: {decoded_payload}")
        except jwt.ExpiredSignatureError:
            print("Token has expired")
        except jwt.InvalidTokenError:
            print("Invalid token")
        return 'unknownpayload'


class PatrolBot(OverseerBot):
    def __init__(self):
        super().__init__()
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
        self.last_invoked_user: str = None

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
            if not whitelist.__contains__(user):
                self.bot.whisper(user, "You are unauthorized.")

            if user == self.bot.username:
                return

            parsed_msg: str = jsonMsg['json']['with'][1][''] if not (message is None) else message

            if parsed_msg == "" or parsed_msg is None:
                return

            cmd, args = cmd_parser.parse(parsed_msg)

            if cmd.startswith('patrol'):
                self.last_invoked_user = user
                if cmd.endswith('set'):
                    self.set_patrol_points(args)
                elif cmd.endswith('start'):
                    self.start_patrol()
                elif cmd.endswith('stop'):
                    self.stop_patrol()
            elif cmd.startswith('overseer'):
                self.last_invoked_user = user
                if cmd.endswith('bind'):
                    self.bot.whisper(user, "Binded.")
                elif cmd.endswith('unbind'):
                    self.bot.whisper(user, "Unbinded.")
                elif cmd.endswith('report'):
                    self.bot.whisper(user, "Report:")
                elif cmd.endswith('receive'):
                    encrypted_msg = super().from_jwt(args[0])
                    handle_chat(user, encrypted_msg, translate, jsonMsg, matches)
            else:
                self.log(f"Unknown message: {parsed_msg}")

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

    def set_patrol_points(self, points: list[Vec3]) -> None:
        # points = re.findall(r'\(([-]?\d+),\s*([-]?\d+),\s*([-]?\d+)\)', message)
        # self.patrol_points = [Vec3(int(x), int(y), int(z)) for x, y, z in points]
        if len(points) <= 1:
            self.log(chalk.red(f"Cannot only set one patrol point! ({self.last_invoked_user})"))
            self.bot.whisper(self.last_invoked_user, f"Cannot only set one patrol point.")

        self.patrol_points = points
        self.log(f"Patrol points set: {points} ({self.last_invoked_user})")
        self.bot.whisper(self.last_invoked_user, f"Set patrol points between {points}.")

    def start_patrol(self) -> None:
        if not self.patrol_points:
            self.log(f"No patrol points set. ({self.last_invoked_user})")
            self.bot.whisper(self.last_invoked_user, "No patrol points set. Use 'patrol set (x,y,z) ...' to set points.")
            return

        self.is_patrolling = True
        self.current_patrol_index = 0
        self.log(f"Starting patrol between {len(self.patrol_points)} points. ({self.last_invoked_user})")
        self.bot.whisper(f"Starting patrol between {len(self.patrol_points)} points.")
        self.move_to_next_point()

    def stop_patrol(self) -> None:
        self.is_patrolling = False
        self.bot.navigate.stop()
        self.log(f"Stopping patrol. ({self.last_invoked_user})")
        self.bot.whisper(self.last_invoked_user, "Stopping patrol.")

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

        # Save Code for later
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
