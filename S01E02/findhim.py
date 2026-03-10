import json
import logging
import os

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


PERSON_SCHEMA = {
    "name": "response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": ["string"],
                "description": "First name of the person."
            },
            "surname": {
                "type": ["string"],
                "description": "Surname of the person."
            },
            "born": {
                "type": ["string"],
                "description": "Year of birth."
            },
            "powerPlant": {
                "type": ["string"],
                "description": "Code of the closest power plant."
            },
            "accessLevel": {
                "type": ["number"],
                "description": "Access level of the person."
            },
        },
        "required": ["name", "surname", "born", "powerPlant", "accessLevel"],
        "additionalProperties": False
    },
}


def get_people():
    return [
        {
            "name": "Cezary",
            "surname": "Żurek",
            "gender": "M",
            "born": 1987,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Jacek",
            "surname": "Nowak",
            "gender": "M",
            "born": 1991,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Oskar",
            "surname": "Sieradzki",
            "gender": "M",
            "born": 1993,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Stanisław",
            "surname": "Kubiak",
            "gender": "M",
            "born": 1993,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Wojciech",
            "surname": "Kruk",
            "gender": "M",
            "born": 1986,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Wojciech",
            "surname": "Bielik",
            "gender": "M",
            "born": 1986,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Wacław",
            "surname": "Jasiński",
            "gender": "M",
            "born": 1986,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        },
        {
            "name": "Tymoteusz",
            "surname": "Żurek",
            "gender": "M",
            "born": 1986,
            "city": "Grudziądz",
            "tags": [
                "transport"
            ]
        }
    ]


def print_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def get_power_plants():
    logger.info("Fetching power plants from the database...")

    response = requests.get(f"https://hub.ag3nts.org/data/{AI_DEVS_API_KEY}/findhim_locations.json")
    response.raise_for_status()

    return response.json()["power_plants"]


def get_location(person):
    logger.info("Fetching location for person: %s %s", person["name"], person["surname"])

    body = {
        "apikey": AI_DEVS_API_KEY,
        "name": person["name"],
        "surname": person["surname"]
    }

    response = requests.post("https://hub.ag3nts.org/api/location", json=body)
    response.raise_for_status()

    return response.json()


calculate_distance_tool = {
    "type": "function",
    "function": {
        "name": "calculate_distance",
        "description": "Calculate distance between two coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "loc1": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude of the first location."
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude of the first location."
                        }
                    },
                },
                "loc2": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude of the second location."
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude of the second location."
                        }
                    },
                },
            },
            "required": ["name"]
        }
    }
}


def calculate_distance(loc1, loc2):
    from math import radians, cos, sin, asin, sqrt

    lat1, lon1 = loc1["latitude"], loc1["longitude"]
    lat2, lon2 = loc2["latitude"], loc2["longitude"]

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    return c * r


get_access_level_tool = {
    "type": "function",
    "function": {
        "name": "get_access_level",
        "description": "Returns access level of the person.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the person.",
                },
                "surname": {
                    "type": "string",
                    "description": "Name of the person.",
                },
                "born": {
                    "type": "number",
                    "description": "Person's birth year.",
                }
            },
            "required": ["name"]
        }
    }
}


def get_access_level(person):
    logger.info("Fetching access level for person: %s %s", person["name"], person["surname"])

    body = {
        "apikey": AI_DEVS_API_KEY,
        "name": person["name"],
        "surname": person["surname"],
        "birthYear": person["born"]
    }

    response = requests.post("https://hub.ag3nts.org/api/accesslevel", json=body)
    response.raise_for_status()

    return response.json()


def call_model(messages, tools=[], response_schema=None):
    logger.info("Calling model...")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": 'openai/gpt-4o-mini',
        "messages": messages,
        "tools": tools,
    }

    if response_schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": response_schema,
        }

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]
        logger.debug(content)
        logger.info("Model responded successfully.")
        return content
    except requests.exceptions.RequestException as ex:
        logger.error(f"Model failed: {ex} ({ex.response.text}")


logger.info("Start searching him...")

people = get_people()
for person in people:
    person["city"] = None
logger.info("Example person: %s", print_json(people[0]))
logger.info("Fetched people: %d", len(people))

power_plants = get_power_plants()
logger.info("Example power plant: %s", print_json(power_plants))
logger.info("Fetched power plants: %d", len(power_plants))

# people_with_locations = []
# for person in people:
#     locations = get_location(person)
#     person_with_locations = person.copy()
#     person_with_locations["locations"] = locations
#     people_with_locations.append(person_with_locations)
#
# logger.info("Example person with locations: %s", print_json(people_with_locations[0]))

messages = [
    {"role": 'system', "content": 'You received two lists: one with persons, second with power plants locations.'},
    {"role": 'system', "content": 'Find person that was closest to any of the power plants based on the coordinates locations.'},
    {"role": 'system', "content": 'Return person data, power plant name and code and minimal distance to the closest power plant.'},
    {"role": 'user', "content": json.dumps(people)},
    {"role": 'user', "content": json.dumps(power_plants)},
]

while True:
    # logger.info("Messages: %s", print_json(messages))
    content = call_model(
        messages=messages,
        tools=[calculate_distance_tool, get_access_level_tool],
        response_schema=PERSON_SCHEMA,
    )
    # logger.info("Model response: %s", content)

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])
            logger.info("Function call requested: %s, arguments: %s", function["name"], function["arguments"])
            if function["name"] == "get_access_level":
                access_level = get_access_level(arguments)
                logger.info("Access level: %s", access_level)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(access_level)
                })
            elif function["name"] == "calculate_distance":
                distance = calculate_distance(arguments["loc1"], arguments["loc2"])
                logger.info("Calculated distance: %s", distance)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps({"distance": distance})
                })
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break

#access_level = get_access_level(json.loads(content["content"]))
#logger.info(access_level)