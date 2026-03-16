import os
import json

import requests
from dotenv import load_dotenv

from common.logs import get_logger
from common.model import call_model
from common.hub import hub_verify


logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_products() -> str:
    response = requests.get(f"{AI_DEVS_HUB_URL}/data/{AI_DEVS_API_KEY}/categorize.csv")
    response.raise_for_status()

    return response.text


categorize_tool = {
    "type": "function",
    "function": {
        "name": "categorize",
        "description": "Categorizes one product based on the given prompt",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Prompt including one product identifier and description to be categorized. Send value reset to reset token balance."
                },
            },
            "required": ["prompt"]
        }
    }
}
def categorize(prompt: str) -> dict:
    return  hub_verify(
        task="categorize",
        answer={"prompt": prompt},
        response_type="text",
    )


messages = [
    {"role": "system", "content": "You are a prompt engineer."},
    {"role": "system", "content": "Create prompt that will use minimal amount of tokens."},
    {"role": "system", "content": "You can test created prompt against each product from the list using provided tool."},
    {"role": "system", "content": "Reset token balance before executing tests against all the products."},
    {"role": "user", "content": "Create prompt that categorizes products based on the description."},
    {"role": "user", "content": "Products should be categorized into one of two categories: DNG - dangerous and NEU - neutral."},
    {"role": "user", "content": "Nuclear reactor parts should be neutral."},
    {"role": "user", "content": "List of products: \n:" + get_products()},
]

while True:
    content = call_model(
        messages=messages,
        tools=[categorize_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])
            logger.info(f"Categorizing {arguments['prompt']}")

            if function["name"] == "categorize":
                content = categorize(arguments["prompt"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": content
            })
            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], content)
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break
