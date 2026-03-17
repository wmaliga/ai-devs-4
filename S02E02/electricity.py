import os
import json

from dotenv import load_dotenv

from common.images import get_base64_image
from common.logs import get_logger
from common.hub import hub_verify
from common.model import call_model


logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


get_map_image_tool = {
    "type": "function",
    "function": {
        "name": "get_map_image",
        "description": "Returns current map state as base64 encoded image",
        "parameters": {}
    }
}
def get_map_image() -> str:
    return get_base64_image(f"{AI_DEVS_HUB_URL}/data/{AI_DEVS_API_KEY}/electricity.png")


def get_solved_map_image() -> str:
    return get_base64_image(f"{AI_DEVS_HUB_URL}/i/solved_electricity.png")


rotate_tile_tool = {
    "type": "function",
    "function": {
        "name": "rotate_tile",
        "description": "Rotates one tile by 90 degree right.",
        "parameters": {
            "type": "object",
            "properties": {
                "tile": {
                    "type": "string",
                    "description": "Tile identifier in format [row]x[column] eg. 2x3"
                },
            },
            "required": ["tile"]
        }
    }
}
def rotate_tile(tile: str) -> dict:
    return hub_verify(
        task="electricity",
        answer={"rotate": tile},
    )


messages = [
    {"role": "system", "content": "You are electric connections planner."},
    {"role": "system", "content": "Use tool to get map of electric connections."},
    {"role": "system", "content": "Plan all the moves and call them without reloading map."},
    {"role": "system", "content": "Tiles are addressed with pattern [row]x[column] eg. 1x2."},
    {"role": "user", "content": "Your goal is to rotate fields to look identical as on the solved example."},
    {"role": "user", "content": "Only one field can be rotated by 90 degrees right in one move."},
    {"role": "user", "content": "Power source is on the left bottom corner of the board."},
    {"role": "user", "content": [
        {"type": "text", "text": "Solved example."},
        {"type": "image_url", "image_url": {"url": get_solved_map_image()}}
    ]},
]

while True:
    content = call_model(
        messages=messages,
        tools=[
            get_map_image_tool,
            rotate_tile_tool
        ],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "get_map_image":
                content = get_map_image()
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": [{"type": "image_url", "image_url": {"url": content}}]
                })
                preview = content[:40]
            elif function["name"] == "rotate_tile":
                content = rotate_tile(arguments["tile"])
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(content)
                })
                preview = json.dumps(content)
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], preview)
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break
