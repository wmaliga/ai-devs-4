import json
import os

import requests
from dotenv import load_dotenv

from common.logs import get_logger
from common.model import call_model


load_dotenv()

logger = get_logger()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


LOCATIONS = {
    "Zabrze": {"latitude": 50.3081, "longitude": 18.7857},
    "Piotrków Trybunalski": {"latitude": 51.4053, "longitude": 19.7032},
    "Grudziądz": {"latitude": 53.4843, "longitude": 18.7526},
    "Tczew": {"latitude": 54.0871, "longitude": 18.7820},
    "Radom": {"latitude": 51.4027, "longitude": 21.1471},
    "Chelmno": {"latitude": 53.3486, "longitude": 18.4237},
    "Żarnowiec": {"latitude": 54.7925, "longitude": 18.0838}
}


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


def get_people() -> list:
    with open("S01E02/people.json", "r") as f:
        return json.load(f)["people"]


def print_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def get_power_plants():
    logger.info("Fetching power plants from the database...")

    response = requests.get(f"{AI_DEVS_HUB_URL}/data/{AI_DEVS_API_KEY}/findhim_locations.json")
    response.raise_for_status()

    return response.json()["power_plants"]


def get_location(person):
    logger.info("Fetching location for person: %s %s", person["name"], person["surname"])

    body = {
        "apikey": AI_DEVS_API_KEY,
        "name": person["name"],
        "surname": person["surname"]
    }

    response = requests.post(f"{AI_DEVS_HUB_URL}/api/location", json=body)
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
            "required": ["loc1", "loc2"]
        }
    }
}


def calculate_distance(loc1, loc2) -> dict:
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
    return {"distance": c * r}


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
            "required": ["name", "surname", "born"]
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

    response = requests.post(f"{AI_DEVS_HUB_URL}/api/accesslevel", json=body)
    response.raise_for_status()

    return response.json()


logger.info("Start searching him...")

people = get_people()
logger.info("Example person: %s", print_json(people[0]))
logger.info("Fetched people: %d", len(people))

power_plants = get_power_plants()

for city, power_plant in power_plants.items():
    location = LOCATIONS.get(city)
    power_plant["location"] = location

logger.info("Example power plant: %s", print_json(power_plants["Żarnowiec"]))
logger.info("Fetched power plants: %d", len(power_plants))

for person in people:
    locations = get_location(person)

    closest = {
        "distance": float("inf")
    }

    for person_location in locations:
        for city, power_plant in power_plants.items():
            power_plant_location = power_plant["location"]
            distance = calculate_distance(person_location, power_plant_location)["distance"]

            if distance < closest["distance"]:
                closest = {
                    "city": city,
                    "code": power_plant["code"],
                    "distance": distance,
                }

    person["closest_power_plant"] = closest

logger.info("Example person with locations: %s", print_json(people))


messages = [
    {"role": 'system', "content": 'You received list of people with closest distance to the power plant.'},
    {"role": 'system', "content": 'Find person that was closest to any of the power plants based on calculated distance.'},
    {"role": 'system', "content": 'Return person data, power plant name and code and minimal distance to the closest power plant.'},
    {"role": 'user', "content": json.dumps(people)},
]

while True:
    content = call_model(
        messages=messages,
        tools=[],
        response_schema=PERSON_SCHEMA,
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "get_access_level":
                content = get_access_level(arguments)
            elif function["name"] == "calculate_distance":
                content = calculate_distance(arguments["loc1"], arguments["loc2"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], content)
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break

access_level = get_access_level(json.loads(content["content"]))
logger.info(access_level)