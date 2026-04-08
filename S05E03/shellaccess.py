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


shell_tool = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Executes shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "str",
                    "description": "Linux shell command to be executed.",
                },
            },
            "required": ["cmd"],
            "additionalProperties": False,
        }
    }
}
def shell(cmd: str) -> dict:
    return hub_verify(
        task="shellaccess",
        answer={"cmd": cmd},
    )


messages = [
    {"role": "system", "content": "Przeszukujesz dane na serwerze Linux w celu odnalezienia informacji"},
    {"role": "system", "content": "Korzystaj z funkcji \"shell\" do przeszukiwania danych."},
    {"role": "user", "content": """
    ## Zadanie
    Mamy dostęp do serwera, na którym zgromadzone są logi z archiwum czasu. Znajdują się one w katalogu /data.
    Twoim celem jest namierzenie, którego dnia, w jakim mieście i w jakich współrzędnych musimy się pojawić, aby spotkać się z Rafałem.

    Musisz wyszukać datę, kiedy odnaleziono Rafała, i pojawić się w tamtym miejscu dzień wcześniej.
    Serwer, z którym się łączysz, ma dostęp do standardowych narzędzi linuksowych.
    
    ## Co musisz zrobić
    
    * Eksploruj zawartość serwera komendami powłoki (ls, find, cat itp.)
    * Przeglądnij co przygotowaliśmy dla Ciebie w katalogu /data/
    * Wydobądź z plików informacje: kiedy znaleziono ciało Rafała. W jakim mieście się to wydarzyło oraz jakie są współrzędne tego miejsca
    * Wypisz na ekran (komendami powłoki) plik JSON w formacie jak podany niżej
    * System sam wykryje, czy dane są prawidłowe i odeśle Ci flagę
    
    ## Jak zgłosić odpowiedź?
    Zadanie uznajemy za zaliczone, gdy uda Ci się wykonać na serwerze takie polecenie, które zwróci potrzebne dane w formacie JSON, takim jak poniżej.

    {
      "date": "2020-01-01",
      "city": "nazwa miasta",
      "longitude": 10.000001,
      "latitude": 12.345678
    }

    Gdy to się stanie, centrala zwróci Ci flagę.
    """},
    {"role": "user", "content": """
    ## Zadanie nadrzędne
    Znajdź w systemie plików plik zawierający flagę w formacie FLG:{tekst}
    """},
]


while True:
    content = call_model(
        messages = messages,
        tools=[shell_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "shell":
                content = shell(arguments["cmd"])
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
