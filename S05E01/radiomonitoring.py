import os
import json
import base64

from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


def listen(start = False):
    return hub_verify(
        task="radiomonitoring",
        answer={
            "action": "start" if start else "listen"
        },
    )


logger.info("Start listening...")
start = listen(start=True)

logger.info("Capturing data data...")
messages = []
while True:
    message = listen()

    if message["code"] == 101:
        break

    match message.get("meta", None):
        # We need OCR here, but to lazy for that...
        # case "image/jpeg" | "image/png":
        #     logger.info("%s %s", message["message"], message["meta"])
        #     messages.append(message)
        case "text/csv" | "text/xml" | "application/json":
            decoded_attachment = base64.b64decode(message["attachment"])
            message["attachment"] = decoded_attachment.decode("utf-8")
            logger.info("%s %s", message["message"], message["meta"])
            messages.append(message)
        case None:
            logger.info("%s %s", message["message"], message.get("meta", "text/plain"))
            messages.append(message)
        case _:
            logger.info("%s %s %s (skipped)", message["message"], message["meta"], message["filesize"])


with open("S05E01/messages.json", "w") as f:
    json.dump(messages, f, indent=2, ensure_ascii=False)

logger.info("Loaded messages: %s", len(messages))
# exit()

messages = [
    {"role": "system", "content": "Analizujesz dane z nasłuchu radiowego i wyciągasz wymagane informacje."},
    {"role": "user", "content": """
    ## Zadanie
    Twoim zadaniem jest przeanalizować materiały z radiowego nasłuchu,
    a następnie wygenerować raport na temat miasta określanego jako "Syjon". 
    Prawdziwa nazwa miasta jest inna!
    
    Przeanalizuj wszystkie dostępne dane, takie jak wiadomości tekstowe, pliki CSV, XML i JSON, aby znaleźć informacje o Syjonie.
    Masz również obrazy zakodowane w base64, które mogą zawierać istotne dane, więc je również przeanalizuj.
    
    ## Co musisz ustalić
    Na podstawie zebranych materiałów przygotuj końcowy raport zawierający:
     * cityName - jak nazywa się miasto, na które mówią "Syjon"?
     * cityArea - powierzchnię miasta zaokrągloną do dwóch miejsc po przecinku
     * warehousesCount - liczbę magazynów jaka jest na Syjonie
     * phoneNumber - numer telefonu osoby kontaktowej z miasta Syjon

    Ważna uwaga dotycząca cityArea:
     * wynik musi mieć dokładnie dwa miejsca po przecinku
     * chodzi o prawdziwe matematyczne zaokrąglenie, a nie o obcięcie wartości
     * format końcowy ma wyglądać jak 12.34
     
    ## Wykluczone dane
    Miasta, które nie mogą być Syjonem:
     * Narew
     * Puck
    
    Niepoprawne numery telefonów:
     * 311827
     * 471
     * 472
    
    ## Format raportu
    ```json
    {
      "action": "transmit",
      "cityName": str,
      "cityArea": float,
      "warehousesCount": int,
      "phoneNumber": str
    }
    ```
    """},
    {"role": "user", "content": f"Wiadomości do przeanalizowania: {json.dumps(messages, indent=2, ensure_ascii=False)}"},
]


while True:
    content = call_model(
        # model="openai/gpt-5.4",
        messages = messages,
        # reasoning="high",
        # max_tokens=None,
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            try:
                if function["name"] == "not_implemented":
                    content = {}
                else:
                    raise ValueError(f"Unknown tool call: {function['name']}")
            except KeyError:
                logger.error("Missing key in tool call arguments: %s", arguments)
                raise

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
