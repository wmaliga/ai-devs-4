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


get_config_tool = {
    "type": "function",
    "function": {
        "name": "get_config",
        "description": "Get current CHRONOS-P1 configuration.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    }
}
def get_config() -> dict:
    return hub_verify(
        task="timetravel",
        answer={
            "action": "getConfig",
        },
    )


configure_tool = {
    "type": "function",
    "function": {
        "name": "configure",
        "description": "Set CHRONOS-P1 configuration parameter.",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "enum": ["day", "month", "year", "syncRatio", "stabilization"]
                },
                "value": {
                    "oneOf": [
                        {
                            "description": "day values",
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 31,
                        },
                        {
                            "description": "month values",
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 12,
                        },
                        {
                            "description": "year values",
                            "type": "integer",
                            "minimum": 1500,
                            "maximum": 2499,
                        },
                        {
                            "description": "syncRatio values (max 2 decimals, must match formula from documentation)",
                            "type": "number",
                            "minimum": 0.00,
                            "maximum": 1.00,
                        },
                        {
                            "description": "stabilization values",
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                        },
                    ]
                }
            },
            "required": ["param", "value"],
            "additionalProperties": False,
        }
    }
}
def configure(param: str, value: int | float) -> dict:
    return hub_verify(
        task="timetravel",
        answer={
            "action": "configure",
            "param": param,
            "value": value,
        },
    )


sync_ratio_tool = {
    "type": "function",
    "function": {
        "name": "sync_ratio",
        "description": "Calculate sync ratio for the provided date.",
        "parameters": {
            "type": "object",
            "properties": {
                "day": {
                    "description": "day value",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 31,
                },
                "month": {
                    "description": "month value",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 12,
                },
                "year": {
                    "description": "year value",
                    "type": "integer",
                    "minimum": 1500,
                    "maximum": 2499,
                }
            },
            "required": ["day", "month", "year"],
            "additionalProperties": False,
        }
    }
}
def sync_ratio(day: int, month: int, year: int) -> dict:
    return {
        "syncRatio": ((day*8 + month*12 + year*7) % 101) / 100,
    }


def user_input() -> dict:
    answer = input("[user_input]: ")
    return {"answer": answer}


def load_documentation() -> str:
    with open("S05E05/timetravel.md", "r") as f:
        return f.read()


messages = [
    {"role": "system", "content": "Jesteś asystentem konfigurującym maszynę czasu."},
    {"role": "system", "content": "Korzystając z dostępnej dokumentacji wykonujesz operacje na API w celu ustawienia maszyny."},
    {"role": "system", "content": "Korzystaj z narzędzia 'get_config' do sprawdzenia obecnej konfiguracji."},
    {"role": "system", "content": "Korzystaj z narzędzia 'configure' do ustawiania parametrów konfiguracji."},
    {"role": "system", "content": "Korzystaj z narzędzia 'sync_ratio' do obliczania sync ratio."},
    {"role": "system", "content": f"dane/timetravel.md\n{load_documentation()}"},
    {"role": "system", "content": """
    ## Data skoków w czasie
    
    Poniżej przedstawiam dokładne daty skoków w czasie:
     Skok nr 1 - 5 listopada 2238
     Skok nr 2 - 10 kwietnia 2026
     Skok nr 3 - 12 listopada 2024
     
    Nie konfiguruj niczego dopóki Cię o to nie poproszę.
    Po konfiguracji API podaj co muszę skonfigurować w UI maszyny.
    
    ## Uwagi
    Odczytaj mi aktualny poziom ochrony i podaj dla każdego skoku.
    """},
]


while True:
    content = call_model(
        model="openai/gpt-5.4",
        messages = messages,
        tools=[
            get_config_tool,
            configure_tool,
            sync_ratio_tool,
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

            if function["name"] == "get_config":
                content = get_config()
            elif function["name"] == "configure":
                content = configure(arguments["param"], arguments["value"])
            elif function["name"] == "sync_ratio":
                content = sync_ratio(arguments["day"], arguments["month"], arguments["year"])
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
            logger.info("[agent]: %s", content["content"].replace("\\n", "\n"))
        except AttributeError:
            logger.error("Incorrect content: %s", content)
            break

        user_response = user_input()["answer"]
        messages.append({"role": "user", "content": user_response})
