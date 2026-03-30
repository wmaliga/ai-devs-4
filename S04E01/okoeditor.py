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


okoeditor_tool = {
    "type": "function",
    "function": {
        "name": "okoeditor",
        "description": "Narzędzie pozwala na komunikację z serwisem \"okoeditor\".",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Dane do zapytania - należy podać jedynie dane z części answer.",
                },
            },
            "required": ["answer"]
        }
    }
}
def okoeditor(answer: dict) -> dict:
    return hub_verify(
        task="okoeditor",
        answer=answer,
    )


messages = [
    {"role": "system", "content": "Jesteś edytorem raportów i zadań, wykonujesz zadania zlecone przez użytkownika w systemie \"okoeditor\"."},
    {"role": "system", "content": "Komunikujesz się z systemem za pomocą narzędzia \"okoeditor\". Na początek wyślij {\"action\": \"help\"}, żeby poznać API."},
    {"role": "system", "content": "Po zakończeniu pracy wyślij do narzędzia \"okoeditor\" akcję \"done\"."},
    {"role": "user", "content": "Zmień klasyfikację incydentu o mieście Skolwin (id: 380792b2c86d9c5be670b3bde48e187b) tak, aby nie był to raport o widzianych pojazdach i ludziach, a o zwierzętach np. bobrach."},
    {"role": "user", "content": "Zadanie o identyfikatorze 380792b2c86d9c5be670b3bde48e187b oznacz jako wykonane. W jego treści wpisz, że widziano tam jakieś zwierzęta np. bobry."},
    {"role": "user", "content": "Dodaj do listy incydentów raport o wykryciu ruchu ludzi w okolicach miasta Komarowo. W tym celu wyedytuj incydent id: ff3313a39099222e325f03b378680e3c"},
    {"role": "user", "content": "Gdy to wszystko wykonasz, uruchom akcję \"done\"."},
    {"role": "user", "content": """
Metody kodowania incydentów: 
###
Kody powiązane z incydentami zawsze mają sześć znaków. Pierwsze cztery oznaczają typ zgłoszenia, a dwa ostatnie to podtyp zgłoszenia.

Kody:
RECO - rekonesans terenu wykrył coś niepokojącego
01 znaleziono broń
02 znaleziono prowiant
03 znaleziono pojazd
04 inne

PROB - badanie zdobytej próbki
01 próbka radiowa
02 próbka ruchu internetowego
03 fizyczny nośnik

MOVE - wykryto ruch
01 człowiek
02 pojazd
03 pojazd + człowiek
04 zwierzęta

Kody zawsze wpisujemy na początku tytułu incydentu."""},
]


while True:
    content = call_model(
        model="openai/gpt-5.4",
        messages = messages,
        tools=[okoeditor_tool],
        reasoning="high",
        max_tokens=4096,
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "okoeditor":
                content = okoeditor(arguments["answer"])
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
