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


mailbox_tool = {
    "type": "function",
    "function": {
        "name": "mailbox",
        "description": "Provides access to mailbox. Provide action and params object. Use action help to get available actions and required params.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform.",
                },
                "page": {
                    "type": "number",
                    "description": "Page number to fetch.",
                },
                "params": {
                    "type": "object",
                    "description": "Additional parameters for the action.",
                }
            },
            "required": ["action"]
        },
    },
}
def mailbox(action: str, page: int = 1, params: dict = {}) -> dict:
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "apikey": os.getenv("AI_DEVS_API_KEY"),
        "action": action,
        "page": page,
        "params": params,
    }

    response = requests.post(f"{AI_DEVS_HUB_URL}/api/zmail", headers=headers, json=body)

    return response.json()



verify_tool = {
    "type": "function",
    "function": {
        "name": "verify",
        "description": "Verify if found data is correct.",
        "parameters": {
            "type": "object",
            "properties": {
                "password": {
                    "type": "string",
                    "description": "Password to the system."
                },
                "date": {
                    "type": "string",
                    "description": "Planned attack date in format YYYY-MM-DD."
                },
                "confirmation_code": {
                    "type": "string",
                    "description": "Confirmation code from the security. Format: SEC-[.]{32}}"
                }
            },
            "required": ["password", "date", "confirmation_code"]
        }
    }
}
def verify(password: str, date: str, confirmation_code) -> dict:
    return hub_verify(
        task="mailbox",
        answer={
            "password": password,
            "date": date,
            "confirmation_code": confirmation_code
        }
    )


messages = [
    {"role": "system", "content": "You are mailbox search agent that can fetch requested data using mailbox tool."},
    {"role": "user", "content": "Search mailbox to identify when the attack at power plant is planned."},
    {"role": "user", "content": "You have to find attack date, password to the workers system and confirmation code."},
    {"role": "user", "content": "Check discovered data using verify tool."},
]

while True:
    content = call_model(
        messages=messages,
        tools=[mailbox_tool, verify_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "mailbox":
                content = mailbox(arguments["action"], arguments.get("page", 1), arguments.get("params", {}))
                preview = json.dumps(content)
            elif function["name"] == "verify":
                content = verify(arguments["password"], arguments["date"], arguments["confirmation_code"])
                preview = json.dumps(content)
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], preview)
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break
