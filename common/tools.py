import time


wait_tool = {
    "type": "function",
    "function": {
        "name": "wait",
        "description": "Wait requested time.",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "Numer of seconds to wait.",
                },
            },
            "required": ["seconds"]
        }
    }
}
def wait(seconds: int) -> dict:
    time.sleep(seconds)
    return {"waited": seconds}
