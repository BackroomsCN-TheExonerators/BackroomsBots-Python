from javascript import require, On, Once, AsyncTask, once, off
from simple_chalk import chalk
import re

# Import required JavaScript libraries
mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
Vec3 = require('vec3')

# Bot configuration
BOT_USERNAME = "PatrolBot"
SERVER_HOST = "localhost"
SERVER_PORT = 25565


class PatrolBot:
    def __init__(self):
        self.bot = mineflayer.createBot({
            'host': SERVER_HOST,
            'port': SERVER_PORT,
            'username': BOT_USERNAME,
            'hideErrors': False
        })

        self.bot.loadPlugin(pathfinder.pathfinder)
        self.patrol_points = []
        self.is_patrolling = False
        self.current_patrol_index = 0

        self.setup_events()

    def setup_events(self):
        @On(self.bot, 'spawn')
        def handle_spawn(this):
            self.log("Bot spawned. Ready for commands!")

        @On(self.bot, 'chat')
        def handle_chat(this, username, message, *args):
            if username == self.bot.username:
                return

            if message.startswith('patrol '):
                self.set_patrol_points(message)
            elif message == 'patrolStart':
                self.start_patrol()
            elif message == 'patrolStop':
                self.stop_patrol()

    def set_patrol_points(self, message):
        points = re.findall(r'\((\d+),\s*(\d+),\s*(\d+)\)', message)
        self.patrol_points = [Vec3(int(x), int(y), int(z)) for x, y, z in points]
        self.log(f"Patrol points set: {self.patrol_points}")

    def start_patrol(self):
        if not self.patrol_points:
            self.log("No patrol points set. Use 'patrol (x,y,z) ...' to set points.")
            return

        self.is_patrolling = True
        self.current_patrol_index = 0
        self.log("Starting patrol...")
        self.move_to_next_point()

    def stop_patrol(self):
        self.is_patrolling = False
        self.log("Stopping patrol.")

    def move_to_next_point(self):
        if not self.is_patrolling:
            return

        goal = self.patrol_points[self.current_patrol_index]
        self.log(f"Moving to point: {goal}")

        self.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(goal.x, goal.y, goal.z, 1))

        @On(self.bot, 'goal_reached')
        def handle_goal_reached(this):
            off(self.bot, 'goal_reached', handle_goal_reached)
            self.log(f"Reached point: {goal}")
            self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            self.move_to_next_point()

    def log(self, message):
        print(chalk.blue(f"[{self.bot.username}] {message}"))


# Create and start the bot
patrol_bot = PatrolBot()