import os
import json
import requests
import zipfile

from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")

TASK_ROOT = "S04E04"


def fetch_notes() -> None:
    response = requests.get(f"{AI_DEVS_HUB_URL}/dane/natan_notes.zip")

    with open(f"{TASK_ROOT}/natan_notes.zip", "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(f"{TASK_ROOT}/natan_notes.zip", "r") as zip_ref:
        zip_ref.extractall(f"{TASK_ROOT}/notes")


def load_notes() -> list[dict]:
    notes = []

    for filename in os.listdir(f"{TASK_ROOT}/notes"):
        filepath = os.path.join(f"{TASK_ROOT}/notes", filename)
        with open(filepath, "r") as file:
            note = file.read()
            notes.append({
                "filename": filename,
                "content": note,
            })

    return notes


filesystem_tool = {
    "type": "function",
    "function": {
        "name": "filesystem",
        "description": "Calls filesystem action with provided parameters. Use {\"action\": \"help\"} to learn the commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "params": {
                    "type": "object",
                    "description": "Dictionary with action name and its parameters.",
                },
            },
            "required": ["params"],
            "additionalProperties": False,
        }
    }
}
def filesystem(params: dict) -> dict:
    return hub_verify(
        task="filesystem",
        answer=params,
    )


logger.info("Fetching notes...")
fetch_notes()

logger.info("Loading notes...")
notes = load_notes()

notes_md = "## Natan's notes:\n\n"

for note in notes:
    notes_md += f"### {note['filename']}\n\n"
    notes_md += f"{note['content']}\n\n"


messages = [
    {"role": "system", "content": "Przetwarzasz dostarczone notatki i organizujesz je w wirtualnym systemie plików."},
    {"role": "system", "content": "Korzystaj z funkcji filesystem do zarządzania plikami i katalogami.."},
    {"role": "user", "content": """
    ## Zadanie
    Twoje zadanie polega na logicznym uporządkowaniu notatek Natana w naszym wirtualnym file systemie.
    Potrzebujemy dowiedzieć się, które miasta brały udział w handlu, jakie osoby odpowiadały za ten handel
    w konkretnych miastach oraz które towary były przez kogo sprzedawane.
    
    W udostępnionym API znajdziesz funkcje do tworzenia plików i katalogów, usuwania ich, listowania katalogów oraz dwie funkcje specjalne:

    - reset - czyści cały filesystem (usuwa wszystkie pliki), zacznij ot tej akcji
    - done - wysyła utworzoną strukturę danych do Centrali w celu weryfikacji zadania. 
    
    ## Example filesystem tool calls
    
    Creating a directory:
    ```json
    {
      "action": "createDirectory",
      "path": "/miasta"
    }
    ```
    
    Creating a file:
    ```json
    {
      "action": "createFile",
      "path": "/miasta/opatowo",
      "content": "Hello World!"
    }
    ```
    
    ## Wymagania
    * Potrzebujemy trzech katalogów: /miasta, /osoby oraz /towary
    * W katalogu /miasta mają znaleźć się pliki o nazwach (w mianowniku) takich jak miasta opisywane przez Natana. W środku tych plików powinna być struktura JSON z towarami, jakie potrzebuje to miasto i ile tego potrzebuje (bez jednostek).
    * W katalogu /osoby powinny być pliki z notatkami na temat osób, które odpowiadają za handel w miastach. Każdy plik powinien zawierać imię i nazwisko jednej osoby i link (w formacie markdown) do miasta, którym ta osoba zarządza.
    * Nazwa pliku w /osoby nie ma znaczenia, ale jeśli nazwiesz plik tak jak dana osoba (z podkreśleniem zamiast spacji), a w środku dasz wymagany link, to system też rozpozna, o co chodzi.
    * W katalogu /towary/ mają znajdować się pliki określające, które przedmioty są wystawione na sprzedaż. We wnętrzu każdego pliku powinien znajdować się link do miasta, które oferuje ten towar. Nazwa towaru to mianownik w liczbie pojedynczej, więc "koparka", a nie "koparki"
    
    ## Oczekiwany filesystem
    Efektem Twojej pracy powinny być takie trzy katalogi wypełnione plikami.
    *Uwaga:* w nazwach plików nie używamy polskich znaków. Podobnie w tekstach w JSON.
    
    ## Przykładowa struktura katalogów i plików
    /osoby/nazwa -> tylko jeden plik na osobę
    /miasta/opalino -> bez rozszerzenia
    /towary/ryz -> musi zawierać markdown link do miasta, które oferuje ten towar np. "[Brudzewo](/miasta/brudzewo)", link moze wskazywać tylko na jedno sprzedające miasto
    
    ## Podpowiedzi
    * Rafał Kisiel to jedna osoba
    """},
    {"role": "user", "content": notes_md},
]


while True:
    content = call_model(
        # model="openai/gpt-5.4",
        messages = messages,
        tools=[filesystem_tool],
        # reasoning="high",
        # max_tokens=4096,
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "filesystem":
                content = filesystem(arguments["params"])
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
