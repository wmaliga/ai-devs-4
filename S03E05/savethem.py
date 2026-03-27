import os
import json

import requests
from dotenv import load_dotenv

from common.logs import get_logger
from common.model import call_model

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


ROUTE_SCHEMA = {
    "name": "response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": ["array"],
                "description": "Array containing steps: [\"vehicle_name\", \"right\", \"right\", \"up\", \"down\", \"up\",\"...\"]."
            }
        },
        "required": ["answer"],
        "additionalProperties": False
    },
}


tool_call_tool = {
    "type": "function",
    "function": {
        "name": "tool_call",
        "description": "Query specific tool with parameter.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Called tool name.",
                },
                "query": {
                    "type": "string",
                    "description": "Tool parameter. Not in natural language.",
                },
            },
            "required": ["name", "query"]
        }
    }
}
def tool_call(name: str, query: str) -> dict:
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "apikey": AI_DEVS_API_KEY,
        "query": query,
    }

    response = requests.post(f"{AI_DEVS_HUB_URL}/api/{name}", headers=headers, json=body)

    return response.json()


tool_search_tool = {
    "type": "function",
    "function": {
        "name": "tool_search",
        "description": "Query available tools.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Request for available tools in natural language.",
                },
            },
            "required": ["query"]
        }
    }
}
def tool_search(query: str) -> dict:
    return tool_call("toolsearch", query)


messages = [
    {"role": "system", "content": "You are playing board game, where you have to plan optimal way to reach the city."},
    {"role": "system", "content": "Use tool_search to learn to get available tools and try to get all the possible information how to plan the route."},
    {"role": "system", "content": "Call specific tool with help query to return usage. You should start with tools: books, map, vehicles."},
    {"role": "system", "content": "Return planned route as JSON array in format: [\"vehicle_name\", \"right\", \"right\", \"up\", \"down\", \"up\",\"...\"] - this should be the only output in your final response. Do not return any additional information."},
    {"role": "user", "content": "The envoy must reach the city of Skolwin."},
    {"role": "user", "content": "The acquired maps always have dimensions of 10x10 fields and contain rivers, trees, rocks, etc."},
    {"role": "user", "content": "Every move consumes fuel (unless you are traveling on foot) and food. Each vehicle has its own resource consumption parameters."},
    {"role": "user", "content": "The faster you move, the more fuel you burn; however, the slower you go, the more rations you consume. This needs to be planned carefully."},
    {"role": "user", "content": "You can exit your chosen vehicle at any time and continue the journey on foot."},
    {"role": "user", "content": "The toolsearch tool can accept both natural language queries and keywords."},
    {"role": "user", "content": "All tools returned by toolsearch accept a query parameter and respond in JSON format, always returning the 3 best-matched results (they do not return all entries!)."},
    {"role": "user", "content": "If you reach the finish field, you will obtain the flag and complete the task (the flag will appear in the preview, the API, and the task debugger)."},
    {"role": "user", "content": "Query for tool \"books\": get books with additional information"},
    {"role": "user", "content": "Query for tool \"map\": accepts only city name"},
    {"role": "user", "content": "Query for tool \"vehicles\": specific vehicle name"},
]

while True:
    content = call_model(
        model="openai/gpt-5.4",
        messages = messages,
        tools=[tool_search_tool, tool_call_tool],
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

            if function["name"] == "tool_search":
                content = tool_search(arguments["query"])
            elif function["name"] == "tool_call":
                content = tool_call(arguments["name"], arguments["query"])
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
