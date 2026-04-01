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


reset_tool = {
    "type": "function",
    "function": {
        "name": "reset",
        "description": "Resets board state, queue and action points to defaults, then rolls partisan position again.",
        "parameters": {}
    }
}
def reset() -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "reset",
        },
    )


create_tool = {
    "type": "function",
    "function": {
        "name": "create",
        "description": "Creates a new transporter or scout unit on the next free spawn slot (A6 -> D6).",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["transporter", "scout"],
                    "description": "Unit type.",
                },
                "passengers": {
                    "type": "string",
                    "description": "1-4 (required only for transporter)",
                },
            },
            "required": ["type"],
            "additionalProperties": False,
        }
    }
}
def create(_type: str, passengers: int | None = None) -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "create",
            "type": _type,
            "passengers": passengers,
        },
    )


move_tool = {
    "type": "function",
    "function": {
        "name": "move",
        "description": "Queues movement of a unit to target field with calculated path (road-only for transporter, shortest orthogonal for scout).",
        "parameters": {
            "type": "object",
            "properties": {
                "object": {
                    "type": "string",
                    "description": "Unit hash.",
                },
                "where": {
                    "type": "string",
                    "description": "A1..K11",
                },
            },
            "required": ["object", "where"],
            "additionalProperties": False,
        }
    }
}
def move(_object: str, where: str) -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "move",
            "object": _object,
            "where": where,
        },
    )


inspect_tool = {
    "type": "function",
    "function": {
        "name": "inspect",
        "description": "Performs scout reconnaissance and appends a log entry based on current scout field.",
        "parameters": {
            "type": "object",
            "properties": {
                "object": {
                    "type": "string",
                    "description": "hash (scout)",
                },
            },
            "required": ["object"],
            "additionalProperties": False,
        }
    }
}
def inspect(_object: str) -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "inspect",
            "object": _object,
        },
    )


dismount_tool = {
    "type": "function",
    "function": {
        "name": "dismount",
        "description": "Removes selected number of scouts from transporter and spawns them on free tiles around vehicle.",
        "parameters": {
            "type": "object",
            "properties": {
                "object": {
                    "type": "string",
                    "description": "hash (transporter)",
                },
                "passengers": {
                    "type": "string",
                    "description": "1-4",
                },
            },
            "required": ["object", "passengers"],
            "additionalProperties": False,
        }
    }
}
def dismount(_object: str, passengers: int) -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "dismount",
            "object": _object,
            "passengers": passengers,
        },
    )


get_objects_tool = {
    "type": "function",
    "function": {
        "name": "getObjects",
        "description": "Returns all currently known units with type, position and identifier.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def get_objects() -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "getObjects",
        },
    )


get_map_tool = {
    "type": "function",
    "function": {
        "name": "getMap",
        "description": "Returns clean map layout.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def get_map() -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "getMap",
        },
    )


search_symbol_tool = {
    "type": "function",
    "function": {
        "name": "searchSymbol",
        "description": "Searches clean map for all locations including object identified by symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "exactly 2 alphanumeric characters (e.g. UL, DR, etc.) - not coordinates",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        }
    }
}
def search_symbol(symbol: str) -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "searchSymbol",
            "symbol": symbol,
        },
    )


get_logs_tool = {
    "type": "function",
    "function": {
        "name": "getLogs",
        "description": "Returns collected inspect log entries.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def get_logs() -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "getLogs",
        },
    )


expenses_tool = {
    "type": "function",
    "function": {
        "name": "expenses",
        "description": "Returns action points spending history (action name and action cost).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def expenses() -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "expenses",
        },
    )


action_cost_tool = {
    "type": "function",
    "function": {
        "name": "actionCost",
        "description": "Returns action points cost rules for all operations.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def action_cost() -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "actionCost",
        },
    )


call_helicopter_tool = {
    "type": "function",
    "function": {
        "name": "callHelicopter",
        "description": "Calls evacuation helicopter to selected destination, but only after any scout confirms a human.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "A1..K11",
                },
            },
            "required": ["destination"],
            "additionalProperties": False,
        }
    }
}
def call_helicopter(destination: str) -> dict:
    return hub_verify(
        task="domatowo",
        answer={
            "action": "callHelicopter",
            "destination": destination,
        },
    )


messages = [
    {"role": "system", "content": "You are playing the game using provided description and tools."},
    {"role": "user", "content": """
## Practical Task
Your task is to locate a partisan hiding in the ruins of Domatowo and carry out an efficient evacuation operation.
You have transporters and scout soldiers at your disposal. You must manage this operation in a way that allows you to
find the person we are looking for without exhausting your action points, and call the helicopter before the situation spirals out of control.
You can move through the city using both transporters and on foot. Transporters are only capable of driving on streets.
Before sending anyone into the field, analyze the terrain layout very carefully. As soon as one of the scouts finds the person,
call the rescue helicopter as quickly as possible.

## Received signal from the partisan
"I survived. The bombs destroyed the city. Soldiers were here, searching for resources; they took the oil. Now it is empty.
I have a weapon, and I am wounded. I've hidden in one of the tallest apartment blocks. I have no food. Help."

## Hints

### What You Have at Your Disposal:

* **Maximum 4 transporters**
* **Maximum 8 scouts**
* **300 action points** for the entire operation
* **An 11x11 grid map** with terrain markings

### The Most Important Action Types Have a Cost:

* **Create a scout:** 5 points
* **Create a transporter:** 5 points base fee plus an additional 5 points for every scout being transported
* **Scout movement:** 7 points per square
* **Transporter movement:** 1 point per square
* **Field inspection:** 1 point
* **Unloading scouts from a transporter:** 0 points

### Reconnaissance
First, familiarize yourself with the layout of the city. You can download the entire map using the `getMap` tool.
Tool will return array representing map in property `grid` and description of each object in property `tiles`,
that includes description and symbol.

You can use `searchSymbol` tool to find all coordinates of a given symbol on the map.

### Creating Units
You can create a transporter with a crew of scouts—here is an example of a 2-person crew using the `create` tool:
`create("transporter", 2)`

You can also send a single scout into the city:
`create("scout")``

### Evacuation
The helicopter can only be called once a scout has located the person. The final call to the `callHelicopter` tool should look like this:
`callHelicopter("F6")`

In the `destination` field, provide the coordinates of the location where the helicopter should arrive. You must specify the square where the scout confirmed the person's presence.

## What You Need to Do

* **Scout the city map** and plan your route to ensure you don’t burn through your action points.
* **Create the appropriate units** and deploy them on the board.
* **Utilize transporters** to reach key locations quickly.
* **Unload scouts** in areas where further reconnaissance must be done on foot.
* **Search squares** using the `inspect` action and analyze the results via `getLogs`.
* **Call the helicopter** using the `callHelicopter` action once you have located the partisan.

If you successfully find the person in hiding and complete the evacuation, Command will send back the flag.
    """},
    #{"role": "user", "content": "## UPDATE\nSearch church first!"}
]


while True:
    content = call_model(
        messages = messages,
        tools=[
            create_tool,
            move_tool,
            inspect_tool,
            dismount_tool,
            get_objects_tool,
            get_map_tool,
            search_symbol_tool,
            get_logs_tool,
            expenses_tool,
            action_cost_tool,
            call_helicopter_tool,
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

            if function["name"] == "create":
                content = create(arguments["type"], arguments.get("passengers", None))
            elif function["name"] == "move":
                content = move(arguments["object"], arguments["where"])
            elif function["name"] == "inspect":
                content = inspect(arguments["object"])
            elif function["name"] == "dismount":
                content = dismount(arguments["object"], arguments["passengers"])
            elif function["name"] == "getObjects":
                content = get_objects()
            elif function["name"] == "getLogs":
                content = get_logs()
            elif function["name"] == "getMap":
                content = get_map()
            elif function["name"] == "searchSymbol":
                content = search_symbol(arguments["symbol"])
            elif function["name"] == "expenses":
                content = expenses()
            elif function["name"] == "actionCost":
                content = action_cost()
            elif function["name"] == "callHelicopter":
                content = call_helicopter(arguments["destination"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], json.dumps(content))
    else:
        try:
            logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        except AttributeError:
            logger.error("Incorrect content: %s", content)
        break
