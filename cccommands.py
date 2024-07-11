from typing import List, Any, Type, Dict
import re

from javascript import require, On, Once, AsyncTask, once, off
mineflayer = require('mineflayer')
navigatePlugin = require('mineflayer-navigate')(mineflayer)
pathfinder = require('mineflayer-pathfinder')
Vec3 = require('vec3')


class CommandBuilder:
    def __init__(self, name: str, *param_types: Type, continued_params: bool = False):
        self.name = name
        self.param_types = param_types
        self.continued_params = continued_params
        self.subcommands: Dict[str, CommandBuilder] = {}

    def add_subcommand(self, subcommand: 'CommandBuilder'):
        self.subcommands[subcommand.name] = subcommand
        return self


class CommandParser:
    def __init__(self):
        self.commands = {}

    def register_command(self, builder: CommandBuilder):
        self.commands[builder.name] = builder

    def parse(self, command_string: str) -> tuple[str, List[Any]]:
        parts = command_string.split(maxsplit=1)
        command_name = parts[0]
        args_string = parts[1] if len(parts) > 1 else ""

        if command_name not in self.commands:
            raise ValueError(f"Unknown command: {command_name}")

        builder = self.commands[command_name]
        return self._parse_command(builder, args_string)

    def _parse_command(self, builder: CommandBuilder, args_string: str) -> tuple[str, List[Any]]:
        if builder.subcommands:
            subcommand_parts = args_string.split(maxsplit=1)
            if not subcommand_parts:
                raise ValueError(f"Subcommand required for '{builder.name}'")
            subcommand_name = subcommand_parts[0]
            subcommand_args = subcommand_parts[1] if len(subcommand_parts) > 1 else ""

            if subcommand_name not in builder.subcommands:
                raise ValueError(f"Unknown subcommand '{subcommand_name}' for '{builder.name}'")

            subbuilder = builder.subcommands[subcommand_name]
            subcmd, args = self._parse_command(subbuilder, subcommand_args)
            return f"{builder.name} {subcmd}", args

        args = []
        if builder.continued_params:
            args = self._parse_continued_params(args_string, builder.param_types[0])
        elif len(builder.param_types) == 1 and builder.param_types[0] == str:
            args = [args_string]
        else:
            args = self._parse_multiple_params(args_string, builder.param_types)

        return builder.name, args

    def _parse_continued_params(self, args_string: str, param_type: Type) -> List[Any]:
        if param_type == Vec3:
            return [self._parse_vec3(s) for s in re.findall(r'\([^)]+\)', args_string)]
        else:
            return args_string.split()

    def _parse_multiple_params(self, args_string: str, param_types: List[Type]) -> List[Any]:
        args = []
        remaining = args_string.strip()

        for param_type in param_types:
            if param_type == str:
                if remaining.startswith('"'):
                    end = remaining.find('"', 1)
                    if end == -1:
                        raise ValueError("Unclosed string argument")
                    arg = remaining[1:end]
                    remaining = remaining[end + 1:].strip()
                else:
                    parts = remaining.split(maxsplit=1)
                    arg = parts[0]
                    remaining = parts[1] if len(parts) > 1 else ""
                args.append(arg)
            elif param_type == bool:
                parts = remaining.split(maxsplit=1)
                arg = parts[0].lower() in ('true', 'yes', '1')
                args.append(arg)
                remaining = parts[1] if len(parts) > 1 else ""
            elif param_type == Vec3:
                match = re.match(r'\([^)]+\)', remaining)
                if not match:
                    raise ValueError(f"Invalid Vec3 format: {remaining}")
                arg = self._parse_vec3(match.group())
                args.append(arg)
                remaining = remaining[match.end():].strip()
            else:
                parts = remaining.split(maxsplit=1)
                arg = param_type(parts[0])
                args.append(arg)
                remaining = parts[1] if len(parts) > 1 else ""

        if remaining:
            raise ValueError(f"Too many arguments provided. Remaining: {remaining}")

        return args

    def _parse_vec3(self, s: str) -> Vec3:
        match = re.match(r'\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)\)', s)
        if match:
            return Vec3(*map(float, match.groups()))
        raise ValueError(f"Invalid Vec3 format: {s}")


# Example usage
parser = CommandParser()

patrol_command = (
    CommandBuilder("patrol")
    .add_subcommand(CommandBuilder("set", Vec3, continued_params=True))
    .add_subcommand(CommandBuilder("stop"))
    .add_subcommand(CommandBuilder("start"))
    .add_subcommand(CommandBuilder("config", str, str))
)

parser.register_command(patrol_command)
parser.register_command(CommandBuilder("cmdout", str))
parser.register_command(CommandBuilder("setPatrol", str, bool))

# Test the parser
commands = [
    'patrol set (20,30,28) (20,30,37) (20,38,49)',
    'patrol stop',
    'patrol start',
    'patrol config "configKey" "configValue"',
    'cmdout "/login Type32__"',
    'cmdout "/tp @a @s"',
    'setPatrol "Main Route" true'
]

for cmd in commands:
    name, args = parser.parse(cmd)
    print(f"Command: {name}")
    print(f"Arguments: {args}")
    print()