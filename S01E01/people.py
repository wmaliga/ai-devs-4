import csv
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model


logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

PERSON_SCHEMA = {
    "name": "response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "people": {
                "type": "array",
                "items": {
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
                        "gender": {
                            "type": ["string"],
                            "enum": ["F", "M"],
                            "description": "Gender of the person, F for female, M for male."
                        },
                        "born": {
                            "type": ["integer"],
                            "description": "Birth year of the person as an integer."
                        },
                        "city": {
                            "type": ["string"],
                            "description": "Birth place of the person."
                        },
                        "tags": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "IT", "transport", "edukacja", "medycyna",
                                    "praca z ludźmi", "praca z pojazdami", "praca fizyczna"
                                ]
                            },
                            "description": "List of tags describing the person's field or work type."
                        }
                    },
                    "required": ["name", "surname", "gender", "born", "city", "tags"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["people"],
        "additionalProperties": False
    }
}


def fetch_people():
    logger.info("Fetching people from the database...")

    try:
        response = requests.get(f"{AI_DEVS_HUB_URL}/data/{AI_DEVS_API_KEY}/people.csv")
        response.raise_for_status()
        logger.info("Data fetched successfully.")
        data = response.content.decode('utf-8')

        # Parse CSV data into a list of dictionaries
        people = []
        reader = csv.DictReader(data.splitlines())
        for row in reader:
            birth_year = int(row["birthDate"][:4])  # Extract the year from birthDate
            age = datetime.now().year - birth_year
            row["age"] = age
            people.append(row)

        return people
    except requests.exceptions.RequestException as ex:
        logger.error(f"Failed to fetch people: {ex}")


def tag_people(people):
    logger.info("Tagging people with AI...")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    body ={
        "model": 'openai/gpt-4o-mini',
        "messages": [
            { "role": 'system', "content": 'Count people on the list' },
            { "role": 'user', "content": json.dumps(people) }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": PERSON_SCHEMA
        }
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        tagged_raw = response.json()["choices"][0]["message"]["content"]
        logger.debug(tagged_raw)
        tagged = json.loads(tagged_raw)["people"]
        logger.info("Tagging completed successfully.")
        return tagged
    except requests.exceptions.RequestException as ex:
        logger.error(f"Failed to tag people: {ex}")


def submit_hub(answer):
    logger.info("Submitting answer to the hub...")

    return hub_verify(
        task="people",
        answer=answer,
    )


logger.info("Start searching people...")

people = fetch_people()
logger.info("Example person: %s", json.dumps(people[0], indent=2, ensure_ascii=False))
logger.info("Fetched people: %d", len(people))

# for person in people:
#     if "flag" in person["job"].lower():
#         logger.info("Found flag in: %s", json.dumps(person, indent=2, ensure_ascii=False))
# exit()

people = [person for person in people if person["birthPlace"] == "Grudziądz"]
logger.info("Filtered by place: %d", len(people))

people = [person for person in people if person["gender"] == "M"]
logger.info("Filtered by gender: %d", len(people))

people = [person for person in people if 20 <= person["age"] <= 40]
logger.info("Filtered by age: %d", len(people))

model_response = call_model(
    messages=[
        {"role": "system", "content": "You are tagging assistant."},
        {"role": "user", "content": "Tag people on the list based on their profession."},
        {"role": "user", "content": json.dumps(people)}
    ],
    response_schema=PERSON_SCHEMA,
)
tagged = json.loads(model_response["content"])["people"]

logger.info("Example tagged: %s", json.dumps(tagged, indent=2, ensure_ascii=False))
logger.info("Tagged people: %d", len(tagged))

transport = [person for person in tagged if "transport" in person["tags"]]
logger.info("People tagged with transport: %s", json.dumps(transport, indent=2, ensure_ascii=False))

hub_response = submit_hub(transport)
logger.info("Hub response: %s", json.dumps(hub_response, indent=2, ensure_ascii=False))
