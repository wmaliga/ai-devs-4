import os
import json

from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


board_tool = {
    "type": "function",
    "function": {
        "name": "board",
        "description": "Send command for robot to move. Return current state of the board and output of the command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to control robot on the board.",
                    "oneOf": [
                        {"const": "start", "description": "Initialize the board."},
                        {"const": "left", "description": "Move robot left."},
                        {"const": "right", "description": "Move robot right."},
                        {"const": "reset", "description": "Restart the game."},
                        {"const": "wait", "description": "Wait one turn."},
                    ]
                },
            },
            "required": ["command"]
        }
    }
}
def board(command: str) -> dict:
    return hub_verify(
        task="reactor",
        answer={"command": command},
    )


messages = [
    {"role": "system", "content": "You are robot control agent that moves robot on the board using board tool."},
    {"role": "user", "content": "Board has size 7 columns x 5 rows."},
    {"role": "user", "content": "Board tool will return board state in property board - it returns description of each row of the board."},
    {"role": "user", "content": "Legend: P - start position / G - destination / B - block that blocks moves / . - empty field."},
    {"role": "user", "content": "Player property describes current robot location."},
    {"role": "user", "content": "Blocks property describes current blocks location and direction - they move only up and down."},
    {"role": "user", "content": "First initialize board using start command."},
    {"role": "user", "content": "You can use wait command to wait if move is not possible - block will change position until next move."},
    {"role": "user", "content": "Your goal is to move robot to the destination location and avoid collisions with blocks."},
]

while True:
    content = call_model(
        messages = messages,
        tools=[board_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "board":
                content = board(arguments["command"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], json.dumps(content))
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break
