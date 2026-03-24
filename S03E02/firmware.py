import os
import json

import requests
from dotenv import load_dotenv

from common.logs import get_logger
from common.model import call_model
from common.tools import wait, wait_tool

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


shell_tool = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Execute shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "Command to be executed. Use help command to get available commands and their usage.",
                },
            },
            "required": ["cmd"]
        }
    }
}
def shell(cmd: str) -> dict:
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "apikey": AI_DEVS_API_KEY,
        "cmd": cmd,
    }

    response = requests.post(f"{AI_DEVS_HUB_URL}/api/shell", headers=headers, json=body)

    return response.json()


messages = [
    {"role": "system", "content": "You are Linux administrator. Your job is to use shell tool to execute commands and achieve the goal provided by user."},
    {"role": "system", "content": "Provided distribution has limited set of commands, start with executing help command to get available commands and their usage."},
    {"role": "system", "content": "You cannot list directories: /etc /root /proc/"},
    {"role": "system", "content": "When you detect .gitignore file read content - you cannot touch files listed there."},
    {"role": "system", "content": "After attempt to access forbidden file use wait tool to await seconds left time. If time is not provided then wait 30 seconds."},
    {"role": "user", "content": "Your task is to run binary: opt/firmware/cooler/cooler.bin"},
    {"role": "user", "content": "Binary file needs password that can be found in multiple places in the filesystem."},
    {"role": "user", "content": "Configure properly file settings.ini"},
    {"role": "user", "content": "Executed binary should print special code in format: ECCS-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
]

while True:
    content = call_model(
        messages = messages,
        tools=[shell_tool, wait_tool],
    )

    if not content:
        logger.error("No content in model response, stopping.")
        break

    if "tool_calls" in content:
        messages.append(content)
        for call in content["tool_calls"]:
            function = call["function"]
            arguments = json.loads(function["arguments"])

            if function["name"] == "shell":
                content = shell(arguments["cmd"])
            elif function["name"] == "wait":
                content = wait(arguments["seconds"])
            else:
                raise ValueError(f"Unknown tool call: {function['name']}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(content)
            })

            logger.info("[%s] arguments: %s -> %s", function["name"], function["arguments"], json.dumps(content))
    else:
        logger.info("Final response: %s", content["content"].replace("\\n", "\n"))
        break
