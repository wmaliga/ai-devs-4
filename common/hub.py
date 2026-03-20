import os

import requests


def hub_verify(task: str, answer: dict, response_type = "json") -> dict | str:
    api_key = os.getenv("AI_DEVS_API_KEY")
    hub_url = os.getenv("AI_DEVS_HUB_URL")

    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "apikey": api_key,
        "task": task,
        "answer": answer
    }

    response = requests.post(f"{hub_url}/verify", headers=headers, json=body)

    if response_type == "json":
        return response.json()
    elif response_type == "text":
        return response.text
    else:
        raise ValueError(f"Unsupported response type: {response_type}")
