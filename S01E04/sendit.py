import base64
import os
import json

import requests
from dotenv import load_dotenv

from common.logs import get_logger
from common.model import call_model


logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


get_document_tool = {
    "type": "function",
    "function": {
        "name": "get_document",
        "description": "Loads document content from the given file name in the text format",
        "parameters": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Document file name, e.g. 'index.md'"
                },
            },
            "required": ["file_name"]
        }
    }
}
def get_document(file_name = "index.md") -> dict:
    response = requests.get(f"{AI_DEVS_HUB_URL}/dane/doc/{file_name}")
    response.raise_for_status()

    return response.text


get_image_tool = {
    "type": "function",
    "function": {
        "name": "get_image",
        "description": "Loads image from the given file name in the base64 format",
        "parameters": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Image file name, e.g. 'image.png'"
                },
            },
            "required": ["file_name"]
        }
    }
}
def get_image(file_name) -> str:
    response = requests.get(f"{AI_DEVS_HUB_URL}/dane/doc/{file_name}")
    response.raise_for_status()

    return base64.b64encode(response.content).decode("utf-8")


messages = [
    {"role": "system", "content": "Wygeneruj poprawnie wypełnioną deklarację transportu w Systemie Przesyłek Konduktorskich."},
    {"role": "system", "content": "Deklaracja musi być ściśle zgodna z formatem wyspecyfikowanym w dokumentacji."},
    {"role": "system", "content": "Pliki dokumentacji możesz ładować za pomocą narzędzia get_document."},
    {"role": "system", "content": "Dokumentacja przesyłek znajduje się w pliku index.md"},
    {"role": "system", "content": "Główny dokument specyfikuje załączniki do dokumentacji w formie tekstowej oraz graficznej."},
    {"role": "system", "content": "Masz załadować i przeanalizować wszystkie załączniki."},
    {"role": "system", "content": "Przejazd może korzystać z tras wyłączonych."},
    {"role": "user", "content": "Nadawca (identyfikator): 450202122"},
    {"role": "user", "content": "Data: 2026-03-15"},
    {"role": "user", "content": "Punkt nadawczy: Gdańsk"},
    {"role": "user", "content": "Punkt docelowy: Żarnowiec"},
    {"role": "user", "content": "Waga: 2,8 tony (2800 kg)"},
    {"role": "user", "content": "Budżet: 0 PP (przesyłka ma być darmowa lub finansowana przez System)"},
    {"role": "user", "content": "Zawartość: kasety z paliwem do reaktora"},
    {"role": "user", "content": "Uwagi specjalne: brak - nie dodawaj żadnych uwag"},
]


while True:
    content = call_model(
        messages=messages,
        tools=[get_document_tool, get_image_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "get_document":
                content = get_document(arguments["file_name"])
            elif function["name"] == "get_image":
                content = get_image(arguments["file_name"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": content
            })
            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], content[:100].replace("\n", " "))
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break