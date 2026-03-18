import os

import requests


def hub_verify(task: str, answer: dict) -> dict:
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "apikey": os.getenv("AI_DEVS_API_KEY"),
        "task": task,
        "answer": answer
    }

    response = requests.post("https://hub.ag3nts.org/verify", headers=headers, json=body)

    return response.json()
