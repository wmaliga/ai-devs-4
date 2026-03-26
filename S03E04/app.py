import os
import csv
import json
from typing import Any

from fastapi import FastAPI, Request
import uvicorn
from dotenv import load_dotenv

from common.logs import get_logger
from common.model import call_model


logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI(title="S03E04")


def print_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def load_data(data_dir: str):
    with open(f"{data_dir}/cities.csv", "r") as f:
        cities = list(csv.DictReader(f))
        # logger.info(cities[0])

    with open(f"{data_dir}/connections.csv", "r") as f:
        connections = list(csv.DictReader(f))
        # logger.info(connections[0])

    with open(f"{data_dir}/items.csv", "r") as f:
        items = list(csv.DictReader(f))
        # logger.info(items[0])

    data = []

    for item in items:
        item_connections = [connection["cityCode"] for connection in connections if connection["itemCode"] == item["code"]]
        item_cities = [city["name"] for city in cities if city["code"] in item_connections]
        data.append({
            "item": item["name"],
            "cities": item_cities
        })

    return data


logger.info("Loading data...")
data = load_data("S03E04/data")

logger.info("Loaded %d items", len(data))


search_item_tool = {
    "type": "function",
    "function": {
        "name": "search_item",
        "description": "Search items by name. Returns list of items with their available cities.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Part of item name to search. Search is case insensitive and looks for provided string in any part of item name.",
                },
            },
            "required": ["name"]
        }
    }
}
def search_item(name: str) -> dict:
    return {
        "items": [item for item in data if name.lower() in item["item"].lower()]
    }


@app.post("/search")
async def search(request: Request) -> dict[str, Any]:
    body = await request.json()
    params = body["params"]

    logger.info("[params] %s", params)

    messages = [
        {"role": "system", "content": "Jesteś asystentem wyszukującamy przedmioty i miejsca ich dostępności."},
        {"role": "system", "content": "Narzędzie wyszukujące przeszukuje listę po nazwie przedmiotu. Wynikiem jest lista przedmiotów wraz z miastami, w których są dostępne."},
        {"role": "system", "content": "Najpierw wyszukaj wszystkie dostępne przedmioty danego typu - potem wybierz ten pasujący do opisu podanego przez użytkownika."},
        {"role": "system", "content": "Nie pytaj użytkownika tylko spróbuj wyszukać przedmiot samodzielnie."},
        {"role": "system", "content": "Maksymalna długość odpowiedzi to 500 bajtów."},
        {"role": "user", "content": f"Zapytanie użytkownika: {params}"},
    ]

    for _ in range(5):
        model_response = call_model(
            messages=messages,
            tools=[search_item_tool]
        )

        if "tool_calls" in model_response:
            for call in model_response["tool_calls"]:
                function = call["function"]
                arguments = json.loads(function["arguments"])

                if function["name"] == "search_item":
                    content = search_item(arguments["name"])
                else:
                    raise ValueError(f"Unknown tool: {function['name']}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(content)
                })

                logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], content)
        else:
            logger.info("[System] %s", model_response["content"])
            break

    return {
        "output": model_response["content"]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="192.168.3.123", port=20323)
    #uvicorn.run(app, host="127.0.0.1", port=8000)

