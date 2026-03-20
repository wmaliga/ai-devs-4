import os
import json

import requests
from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


def get_documentation() -> str:
    response = requests.get(f"{AI_DEVS_HUB_URL}/dane/drone.html")
    return response.text


drone_control_tool = {
    "type": "function",
    "function": {
        "name": "drone_control",
        "description": "Send command instructions to the drone.",
        "parameters": {
            "type": "object",
            "properties": {
                "instructions": {
                    "type": "array",
                    "description": "List of instructions for the drone. Each instruction should be a string command",
                    "items": {
                        "type": "string"
                    }
                },
            },
            "required": ["instructions"]
        }
    }
}
def drone_control(instructions: list[str]) -> dict:
    return hub_verify(
        task="drone",
        answer={"instructions": instructions}
    )


logger.info("Analyzing terrain map to find dam location...")

# content = call_model(
#     messages = [
#         {"role": "system", "content": "You analyze pictures and return requested data."},
#         {"role": "user", "content": "Please analyze terrain map and return dam location using grid coordinates."},
#         {"role": "user", "content": "Return data as {column},{row} - no extra data. Upper left corner is 1,1."},
#         {"role": "user", "content": [
#             {"type": "text", "text": "Terrain map with grid."},
#             {"type": "image_url", "image_url": {"url": f"{AI_DEVS_HUB_URL}/data/{AI_DEVS_API_KEY}/drone.png"}},
#         ]},
#     ],
# )
#
# dam_coordinates = content["content"]
dam_destination_id = "PWR6132PL"
dam_coordinates = "2,4"
logger.info("Dam coordinates: %s", dam_coordinates)


messages = [
    {"role": "system", "content": "You are drone operator. You use drone control tool and documentation to realize mission from user."},
    {"role": "system", "content": f"Documentation:\n\n{get_documentation()}"},
    {"role": "user", "content": f"Your mission is to fly drone to the dam located at destination ID {dam_destination_id} and drop bomb at coordinates: {dam_coordinates}."},
#   {"role": "user", "content": "Provide instruction how to fulfill the mission."},
]

while True:
    content = call_model(
        messages = messages,
        tools=[drone_control_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "drone_control":
                content = drone_control(arguments["instructions"])
                preview = json.dumps(content)
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], preview)
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break
