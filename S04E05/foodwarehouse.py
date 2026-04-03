import os
import json
import requests

from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")

TASK_ROOT = "S04E05"


def fetch_data() -> None:
    response = requests.get(f"{AI_DEVS_HUB_URL}/dane/food4cities.json")

    with open(f"{TASK_ROOT}/dane/food4cities.json", "wb") as f:
        f.write(response.content)


def load_data() -> dict:
    return json.load(open(f"{TASK_ROOT}/dane/food4cities.json"))


warehouse_tool = {
    "type": "function",
    "function": {
        "name": "warehouse",
        "description": "Calls warehouse management tools. Use {\"tool\": \"help\"} to learn the commands. Tool property is obligatory.",
        "parameters": {
            "type": "object",
            "properties": {
                "params": {
                    "type": "object",
                    "description": "Dictionary with tool name and its parameters.",
                },
            },
            "required": ["params"],
            "additionalProperties": False,
        }
    }
}
def warehouse(params: dict) -> dict:
    return hub_verify(
        task="foodwarehouse",
        answer=params,
    )


logger.info("Fetching food requirements...")
# fetch_data()

logger.info("Loading data...")
data = load_data()

logger.info("Loaded cities: %s", len(data.keys()))
logger.info("Data example: %s", json.dumps(data["domatowo"]))


messages = [
    {"role": "system", "content": "Planujesz zamówienia w systemie magazynowym."},
    {"role": "system", "content": "Korzystaj z funkcji \"warehouse\" do komunikacji z magazynem."},
    {"role": "user", "content": """
    ## Zadanie
    Musisz uporządkować pracę magazynu żywności i narzędzi tak, aby przygotować zamówienia,
    które zaspokoją potrzeby wszystkich wskazanych miast. Do dyspozycji dostajesz gotowe API magazynu,
    generator podpisów bezpieczeństwa oraz dostęp tylko do odczytu do bazy danych, z której trzeba wyciągnąć
    dane potrzebne do autoryzacji zamówienia.
    
    ## Jak działa API
    Najważniejsze narzędzia:
    * orders - odczyt, tworzenie, uzupełnianie i usuwanie zamówień
    * signatureGenerator - generowanie podpisu SHA1 na podstawie danych użytkownika z bazy SQLite
    * database - odczyt danych i schematów z bazy SQLite
    * reset - przywrócenie początkowego stanu zamówień
    * done - końcowa weryfikacja rozwiązania
    
    ## Przykładowe zapytania warehouse
    
    ### Praca z zamówieniami
    
    Możesz pobrać listę aktualnych zamówień:
    ```json
    {
      "tool": "orders",
      "action": "get"
    }
    ```
    
    Nowe zamówienie tworzysz dopiero wtedy, gdy znasz już tytuł, creatorID, kod destination oraz poprawny podpis::
    ```json
    {
      "tool": "orders",
      "action": "create",
      "title": "Dostawa dla Torunia",
      "creatorID": 2,
      "destination": "1234",
      "signature": "tutaj-podpis-sha1"
    }
    ```
    
    Po utworzeniu zamówienia możesz dopisywać towary pojedynczo:
    ```json
    {
      "tool": "orders",
      "action": "append",
      "id": "tutaj-id-zamowienia",
      "name": "woda",
      "items": 120
    }
    ```
    
    Możesz też użyć batch mode i dopisać wiele pozycji naraz. To ważne, bo orders.append przyjmuje również obiekt z wieloma towarami:
    ```json
    {
      "chleb": 45,
      "woda": 120,
      "mlotek": 6
    }
    ```
    
    Jeżeli dopiszesz do zamówienia towar, który już w nim istnieje, system zwiększy jego ilość zamiast tworzyć duplikat.
    
    ### Odczyt bazy SQLite
    
    Możesz sprawdzić, jakie tabele znajdują się w bazie:
    ```json
    {
      "tool": "database",
      "query": "show tables"
    }
    ```
    
    Możesz też wykonywać zapytania select:
    ```json
    {
      "tool": "database",
      "query": "select * from tabela"
    }
    ```
    
    ### Zakończenie zadania
    
    Gdy uznasz, że wszystkie wymagane zamówienia są gotowe, wyślij finalne sprawdzenie:
    ```json
    {
      "tool": "done"
    }
    ```
    
    Jeśli komplet zamówień będzie zgodny z potrzebami miast, trafi pod właściwe kody docelowe i zachowa poprawne podpisy, Centrala odeśle flagę.
    
    ## Co musisz zrobić
    
    * Ustal, które miasta biorą udział w operacji na podstawie pliku food4cities.json
    * Znajdź odpowiednie wartości dla pola destination dla tych miast
    * Odczytaj z food4cities.json, jakie towary i ilości są potrzebne w każdym z tych miast
    * Przygotuj osobne zamówienie dla każdego wymaganego miasta
    * Każde zamówienie utwórz z poprawnym creatorID, destination i podpisem wygenerowanym na podstawie danych z bazy SQLite
    * Uzupełnij zamówienia dokładnie tymi towarami, których potrzebują miasta. Bez braków i bez nadmiarów
    * Gdy wszystko będzie gotowe, wywołaj narzędzie done
    
    ## Podpowiedzi
    * Musisz utworzyć tyle zamówień, ile mamy miast w pliku JSON
    * Jeśli coś zepsujesz po drodze, użyj reset, żeby wrócić do stanu początkowego
    * Każde zamówienie musi mieć poprawny creatorID oraz signature
    """},
    {"role": "user", "content": f"Zawartość pliku food4cities.json: {json.dumps(data)}"},
]


while True:
    content = call_model(
        model="openai/gpt-5.4",
        messages = messages,
        tools=[warehouse_tool],
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

            try:
                if function["name"] == "warehouse":
                    content = warehouse(arguments)
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
