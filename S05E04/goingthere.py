import os
import json
import hashlib

from dotenv import load_dotenv
import requests

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model
from common.tools import wait

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")
MAX_RETRIES = 10
WAIT_SECONDS = 5


command_tool = {
    "type": "function",
    "function": {
        "name": "command",
        "description": "Controls rocket by sending command to one move.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["start", "go", "left", "right"],
                    "description": "Command for rocket move.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        }
    }
}
def command(_command: str) -> dict:
    return hub_verify(
        task="goingthere",
        answer={
            "command": _command,
        },
    )


get_message_tool = {
    "type": "function",
    "function": {
        "name": "get_message",
        "description": "Returns information about obstacles ahead the rocket.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def get_message() -> dict:
    url = f"{AI_DEVS_HUB_URL}/api/getmessage"
    headers = {"Content-Type": "application/json"}
    body = {"apikey": AI_DEVS_API_KEY}

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()


scanner_tool = {
    "type": "function",
    "function": {
        "name": "scanner",
        "description": "Returns information about traps. Response contains frequency and the detection code",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def scanner() -> str:
    url = f"{AI_DEVS_HUB_URL}/api/frequencyScanner?key={AI_DEVS_API_KEY}"
    headers = {"Content-Type": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException:
            if attempt < MAX_RETRIES - 1:
                logger.warning("[scanner] Retry %d", attempt + 1)
                wait(WAIT_SECONDS)
            else:
                raise

    raise Exception("[scanner] Max retries reached!")


disarm_tool = {
    "type": "function",
    "function": {
        "name": "disarm",
        "description": "Disarms trap using frequency and detection code.",
        "parameters": {
            "type": "object",
            "properties": {
                "frequency": {
                    "type": "number",
                    "description": "Frequency returned by scanner.",
                },
                "detectionCode": {
                    "type": "string",
                    "description": "Detection code returned by scanner.",
                },
            },
            "required": ["frequency", "detectionCode"],
            "additionalProperties": False,
        }
    }
}
def disarm(frequency: int, detection_code: str) -> dict:
    url = f"{AI_DEVS_HUB_URL}/api/frequencyScanner"
    headers = {"Content-Type": "application/json"}
    body = {
        "apikey": AI_DEVS_API_KEY,
        "frequency": frequency,
        "disarmHash": hashlib.sha1(f"{detection_code}disarm".encode("utf-8")).hexdigest(),
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("[disarm] Request failed: %s", e)
        logger.error("[disarm] Body: %s", json.dumps(body, indent=2))
        raise


messages = [
    {"role": "system", "content": "You play a game where you control rocket and avoid obstacles."},
    {"role": "user", "content": """
    ## Rocket Control

    The rocket moves on a grid consisting of 3 rows and 12 columns.
    The starting point is always in Column 1, Row 2 (the middle row). The base in Grudziądz is located in Column 12,
    in a row specified at the start of the game. Each column contains exactly one rock (obstacle).
    
    You have three movement commands and one starting command at your disposal:
     * start – begins a new game, generates a new map, and resets all settings.
     * go – flies straight ahead (stays in the same row, moves to the next column).
     * left – moves to a higher row and forward (up + next column).
     * right – moves to a lower row and forward (down + next column).
    
    Rules and Constraints:
     * Movement: Every move advances the rocket exactly one column forward (including left and right).
     * Collisions: If you hit a rock, the rocket crashes and you must start over.
     * Boundaries: If you move outside the grid boundaries, the rocket crashes.
     * Radars: If you fail to neutralize the radar system, you will be shot down.
    
    You move using "command" tool.
    
    ## Radio Hints Regarding Rocks

    Since the path ahead is not visible, you can request a radio hint.

    Description:
    The response will contain a "hint" field with a message in English. This message describes the position of
    the rock in the next column relative to the rocket (left, right, or straight ahead). Based on this information,
    you must decide which movement command to send to avoid hitting the rock.

    [!IMPORTANT]
    Note: Radio messages can sometimes be unusual and may use nautical (maritime) terminology.
    
    You get radio hints "get_message" tool.

    ## Frequency Scanner and OKO System Scanners
    
    The route is equipped with **OKO System scanners**, but their locations are unknown.
    If the rocket is in a column with an active trap and you attempt to move without neutralizing it,
    the rocket will be shot down.
    
    To check if you are being targeted, query the frequency scanner using the "scanner" tool.

    The scanner will return one of two responses:
    
    * **Safe Status:** The response will contain the text: `"It's clear!"`
    * **Targeted Status:** The response will contain a **JSON-like object** with several fields.
        Most importantly, it will include the **targeting frequency** and a **string of characters** required to generate the radar annihilation code.
    
    > [!WARNING]
    > **Important:** Scanner responses are distorted by jamming systems. The data you receive may look like JSON,
    but it might not be immediately parsable and may require cleaning or manual handling.
    
    Oto tłumaczenie ostatniej części instrukcji na język angielski:

    ## Trap Neutralization
    
    Once the scanner detects that you are being targeted, you must neutralize the trap before making your next move.

    To disarm trap use "disarm" tool with frequency and code received from the "scanner" tool.

    If the data is correct, the trap will be disarmed, and you will be able to continue your flight safely.
    
    ## Your Tasks

    1.  **Initialize the game:** Execute the `start` command and take note of the destination base's position.
    2.  **Check for threats:** At every step, query the `scanner` tool first to check if you are being targeted.
    3.  **Neutralize traps:** If you are being targeted, parse the distorted scanner response to extract the `detectionCode` and `frequency`. Use 'disarm' tool to neutralize the trap before proceeding.
    4.  **Get navigation hints:** Retrieve a radio hint from the `get_message` endpoint to determine the location of the rock in the next column.
    5.  **Execute movement:** Based on the hint, choose the appropriate movement command (`go`, `left`, or `right`) and move the rocket. **Note:** Ensure you do not move outside the grid boundaries.
    6.  **Loop:** Repeat steps 2 through 5 until you reach the base in Grudziądz.
    7.  **Retrieve the flag:** Once the rocket reaches Grudziądz, you will receive the flag. Display it.
    
    ## Extra hints
    1.  Stop playing after you crush the rocket.
    2.  Current rocket position is returned in 'row' property
    3.  You cannot move left from row 1 and cannot move right from row 3.
    """},
]


while True:
    content = call_model(
        model="openai/gpt-5.4",
        messages = messages,
        tools=[
            command_tool,
            get_message_tool,
            scanner_tool,
            disarm_tool,
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

            if function["name"] == "command":
                content = command(arguments["command"])
            elif function["name"] == "get_message":
                content = get_message()
            elif function["name"] == "scanner":
                content = scanner()
            elif function["name"] == "disarm":
                content = disarm(arguments["frequency"], arguments["detectionCode"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], json.dumps(content, ensure_ascii=False))
    else:
        try:
            logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        except AttributeError:
            logger.error("Incorrect content: %s", content)
        break
