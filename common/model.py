import os
import logging

import requests

logger = logging.getLogger(__name__)


def call_model(messages, model="google/gemini-3.1-flash-lite-preview", tools=[], response_schema=None):
    logger.debug("Calling model...")

    api_key = os.getenv("OPENROUTER_API_KEY")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": messages,
        "tools": tools,
    }

    if response_schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": response_schema,
        }

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        logger.debug(message)
        logger.debug("Model responded successfully.")
        return message
    except requests.exceptions.RequestException as ex:
        logger.error(f"Model failed: {ex} ({ex.response.text}")
