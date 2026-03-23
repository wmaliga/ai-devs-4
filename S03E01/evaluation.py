import os
import json
import zipfile

import requests
from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


def fetch_sensor_readings() -> None:
    response = requests.get(f"{AI_DEVS_HUB_URL}/dane/sensors.zip")

    with open("S03E01/sensors.zip", "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile("S03E01/sensors.zip", "r") as zip_ref:
        zip_ref.extractall("S03E01/sensors")


def load_sensor_readings() -> list[dict]:
    readings = []

    for filename in os.listdir("S03E01/sensors"):
        if filename.endswith(".json"):
            filepath = os.path.join("S03E01/sensors", filename)
            with open(filepath, "r") as file:
                reading = json.load(file)
                reading["name"] = filename[:-5]
                readings.append(reading)

    return readings


def print_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


logger.info("Fetching sensor readings...")
#fetch_sensor_readings()

logger.info("Loading sensor readings...")
readings = load_sensor_readings()
logger.info("Loaded %d readings", len(readings))
#logger.info("Example reading: %s", print_json(readings[0]))

type_properties = {
    "temperature": {"property": "temperature_K", "min": 553, "max": 873},
    "pressure": {"property": "pressure_bar", "min": 60, "max": 160},
    "water": {"property": "water_level_meters", "min": 5.0, "max": 15.0},
    "voltage": {"property": "voltage_supply_v", "min": 229.0, "max": 231.0},
    "humidity": {"property": "humidity_percent", "min": 40.0, "max": 80.0},
}

reading_to_sensor = {
    "temperature_K": "temperature",
    "pressure_bar": "pressure",
    "water_level_meters": "water",
    "voltage_supply_v": "voltage",
    "humidity_percent": "humidity",
}

def verify_all_readings(reading, sensor_types) -> bool:
    for reading_property, sensor_type in reading_to_sensor.items():
        if reading[reading_property] != 0 and sensor_type not in sensor_types:
            return False

    return True


def verify_single_reading(reading, sensor_type) -> bool:
    spec = type_properties[sensor_type]
    prop = spec["property"]
    minimum = spec["min"]
    maximum = spec["max"]
    value = reading[prop]

    return minimum <= value <= maximum


for reading in readings:
    sensor_types = reading["sensor_type"].split("/")

    all_readings_valid = verify_all_readings(reading, sensor_types)

    if not all_readings_valid:
        reading["values_valid"] = False
        continue

    reading["values_valid"] = True

    for sensor_type in sensor_types:
        values_valid = verify_single_reading(reading, sensor_type)

        if not values_valid:
            reading["values_valid"] = values_valid
            break


invalid_readings = [r for r in readings if not r["values_valid"]]
logger.info("Invalid readings: %d", len(invalid_readings))
logger.info("Invalid example: %s", print_json(invalid_readings[10]))

NOTE_SCHEMA = {
    "name": "response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "valid": {
                "type": "boolean",
                "description": "True if the note indicates that the reading is valid, otherwise False."
            }
        },
        "required": ["valid"],
        "additionalProperties": False
    }
}

logger.info("Evaluating readings programmatically...")
# Only God can judge me for this part...
positive_parts = [
    "All telemetry looks steady",
    "Daily monitoring confirms stability",
    "Current status remains health",
    "Everything checks out",
    "Execution quality is high",
    "Health indicators remain strong",
    "No concerning drift is present",
    "No irregular behavior is visible",
    "No warning signs appeared",
    "Observed values stay controlled",
    "Operational state is consistent",
    "Performance appears nominal",
    "Readings are calm and predictable",
    "Routine diagnostics are positive",
    "System behavior is fully stable",
    "The operating profile stays normal",
    "The overall picture is solid",
    "The latest report looks clean",
    "The process stayed balanced",
    "The recent snapshot is reassuring",
    "The trend line is quiet",
    "This cycle looks reliable",
    "This run finished without surprises",
    "Tracking data remains coherent",
    "Service condition is excellent",
]
negative_parts = []
missing = 0

for reading in readings:
    operator_notes = reading["operator_notes"]

    if any(part in operator_notes for part in positive_parts):
        reading["operator_valid"] = True
    elif any(part in operator_notes for part in negative_parts):
        reading["operator_valid"] = False

    if "operator_valid" in reading:
        #logger.info("[IDENTIFIED] %s -> %s", operator_notes, reading["operator_valid"])
        pass
    else:
        #logger.info("[MISSING] %s", operator_notes)
        missing += 1

logger.info("Missing evaluations: %d", missing)

logger.info("Evaluating operator notes with the model...")

messages = [
    {"role": "system", "content": "Evaluate the following note and determine if it indicates that the reading is valid or not."}
]

for reading in readings:
    operator_notes = reading["operator_notes"]

    if "operator_valid" not in reading:
        model_response = call_model(
            messages = [
                *messages,
                {"role": "user", "content": operator_notes},
            ],
            response_schema=NOTE_SCHEMA,
        )
        operator_valid = json.loads(model_response["content"])["valid"]
        reading["operator_valid"] = operator_valid
        logger.info("[MODEL EVAL] %s -> %s", operator_notes, operator_valid)


invalid_readings = []

for reading in readings:
    if not reading["values_valid"]:
        invalid_readings.append(reading["name"])
    if reading["values_valid"] != reading["operator_valid"]:
        invalid_readings.append(reading["name"])

logger.info("Invalid readings: %s", invalid_readings)

response = hub_verify(
    task="evaluation",
    answer={"recheck": invalid_readings}
)

logger.info("Hub response: %s", print_json(response))
