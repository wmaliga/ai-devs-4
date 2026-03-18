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


def get_log() -> str:
    response = requests.get(f"{AI_DEVS_HUB_URL}/data/{AI_DEVS_API_KEY}/failure.log")
    response.raise_for_status()

    return response.text


analyze_log_tool = {
    "type": "function",
    "function": {
        "name": "analyze_log",
        "description": "Analyzes log content and identifies the most important lines that are relevant to the failure. Returns hints.",
        "parameters": {
            "type": "object",
            "properties": {
                "logs": {
                    "type": "string",
                    "description": "Optimized log content to analyze. Maximum size is 1500 tokens."
                },
            },
            "required": ["logs"]
        }
    }
}


def analyze_log(logs: str) -> dict:
    return hub_verify(
        task="failure",
        answer={"logs": logs}
    )


log = get_log()
logger.info("Log size: %d lines - %d characters ~ %d tokens", log.count("\n"), len(log), len(log) // 4)
logger.debug("First line: %s", log.splitlines()[0])

messages = [
    {"role": "system", "content": "You are log size optimizer - do not search for failure cause, your task is only to optimize log content."},
    {"role": "system", "content": "Your task is to optimize the log content by removing unnecessary lines while keeping the important information."},
    {"role": "system", "content": "Paraphrase each log message to be as short as possible while keeping the original meaning."},
    {"role": "system", "content": "You cannot change message order and you should keep all important information in the log."},
    {"role": "system", "content": "Use analyze log tool to verify optimized log content and apply tool hints in next iterations."},
    {"role": "system", "content": "Correct log will return status code 0 from analyze tool."},
    {"role": "user", "content": "Do not remove information about firmware."},
    {"role": "user", "content": f"Log content:\n\n{log}"},
]

while True:
    content = call_model(
        model="openai/gpt-5.4",
        messages=messages,
        tools=[analyze_log_tool],
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

            if function["name"] == "analyze_log":
                content = analyze_log(arguments["logs"])
                preview = json.dumps(content)
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"][:30], preview)
    else:
        try:
            logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        except Exception:
            logger.error("Incorrect content: %s", content)
        break
