import os
import json
import threading

from dotenv import load_dotenv

from common.hub import hub_verify
from common.logs import get_logger, elpased
from common.model import call_model
from common.tools import wait

logger = get_logger()

load_dotenv()

AI_DEVS_API_KEY = os.getenv("AI_DEVS_API_KEY")
AI_DEVS_HUB_URL = os.getenv("AI_DEVS_HUB_URL")


start_tool = {
    "type": "function",
    "function": {
        "name": "start",
        "description": "Starts a new service window and initializes task state.",
        "parameters": {}
    }
}
def start() -> dict:
    return hub_verify(
        task="windpower",
        answer={
            "action": "start",
        },
    )


get_tool = {
    "type": "function",
    "function": {
        "name": "get",
        "description": "Requests task data. For weather, turbinecheck, and powerplantcheck use getResult to fetch final response. Documentation is returned directly.",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "enum": [
                        "weather",
                        "turbinecheck",
                        "powerplantcheck",
                        "documentation"
                    ],
                    "description": "Requested data source.",
                },
            },
            "required": ["param"],
            "additionalProperties": False,
        }
    }
}
def get(param: str) -> dict:
    return hub_verify(
        task="windpower",
        answer={
            "action": "get",
            "param": param,
        },
    )


get_result_tool = {
    "type": "function",
    "function": {
        "name": "get_result",
        "description": "Returns one completed queued response with sourceFunction field. Retrieved item is removed from queue.",
        "parameters": {}
    }
}
def get_result() -> dict:
    return hub_verify(
        task="windpower",
        answer={
            "action": "getResult",
        },
    )


config_tool = {
    "type": "function",
    "function": {
        "name": "config",
        "description": "Stores scheduling config points. turbineMode: 'production' enables generation, 'idle' disables turbine. unlockCode is required for every point.",
        "parameters": {
            "type": "object",
            "properties": {
                "startDate": {
                    "type": "string",
                    "description": "Date for config point in format YYYY-MM-DD.",
                },
                "startHour": {
                    "type": "string",
                    "description": "Hour for config point in format HH:00:00.",
                },
                "pitchAngle": {
                    "type": "integer",
                    "description": "Pitch angle for turbine blades in degrees.",
                },
                "turbineMode": {
                    "type": "string",
                    "enum": [
                        "production",
                        "idle",
                    ],
                },
                "unlockCode": {
                    "type": "string",
                    "description": "Code required to unlock config point.",
                },
            },
            "required": ["startDate", "startHour", "pitchAngle", "turbineMode", "unlockCode"],
            "additionalProperties": False,
        }
    }
}
def config(start_date: str, start_hour: str, pitch_angle: int, turbine_mode: str, unlock_code: str) -> dict:
    return hub_verify(
        task="windpower",
        answer={
            "action": "config",
            "startDate": start_date,
            "startHour": start_hour,
            "pitchAngle": pitch_angle,
            "turbineMode": turbine_mode,
            "unlockCode": unlock_code,
        },
    )


unlock_code_generator_tool = {
    "type": "function",
    "function": {
        "name": "unlockCodeGenerator",
        "description": "Generates unlockCode signature for given configuration. Result is asynchronous and must be collected with getResult.",
        "parameters": {
            "type": "object",
            "properties": {
                "startDate": {
                    "type": "string",
                    "description": "Date for config point in format YYYY-MM-DD.",
                },
                "startHour": {
                    "type": "string",
                    "description": "Hour for config point in format HH:00:00.",
                },
                "windMs": {
                    "type": "integer",
                    "description": "Wind speed in m/s.",
                },
                "pitchAngle": {
                    "type": "integer",
                    "description": "Pitch angle for turbine blades in degrees.",
                },
            },
            "required": ["startDate", "startHour", "windMs", "pitchAngle"],
            "additionalProperties": False,
        }
    }
}
def unlock_code_generator(start_date: str, start_hour: str, wind_ms: int, pitch_angle: int) -> dict:
    return hub_verify(
        task="windpower",
        answer={
            "action": "unlockCodeGenerator",
            "startDate": start_date,
            "startHour": start_hour,
            "windMs": wind_ms,
            "pitchAngle": pitch_angle,
        },
    )


done_tool = {
    "type": "function",
    "function": {
        "name": "done",
        "description": "Validates final configuration and returns flag on success.",
        "parameters": {}
    }
}
def done() -> dict:
    return hub_verify(
        task="windpower",
        answer={
            "action": "done",
        },
    )

logger.info("Starting session...")
elpased()
start()

data = {}
logger.info("Prefetching data...")
for param in ["weather", "turbinecheck", "powerplantcheck"]:
    logger.info("[get] %s", param)
    get(param)

logger.info("[get] documentation")
data["documentation"] = get("documentation")

for i in range(40):
    logger.info("[getResult] Elapsed time: %d %s)", elpased(), list(data.keys()))

    result = get_result()
    if "sourceFunction" in result:
        source_function = result["sourceFunction"]
        data[source_function] = result
        continue

    wait(1)
    if len(data.keys()) == 4:
        break


messages = [
    {"role": "system", "content": "You are wind turbine configuration assistant."},
    {"role": "user", "content": """
    ## Task Overview
    Your task is to program the work schedule of a wind turbine in such a way as to obtain the power necessary to start the power plant.

    The power plant cannot operate all the time because its battery will not allow it.
    Therefore, you must start its system only when it is truly required. You are able to find the ideal time by analyzing weather forecast results.

    The APIs we provide also give you information about the status of the turbine itself and the power plant's requirements.
    Preparing a report for each function takes time. We cannot say exactly how much time it will take to execute a given function,but these calls are queued.
    Later, you only need to call a function to retrieve the generated reports.

    Each generated report can only be downloaded once. If you manage to configure everything within 40 seconds, we are saved and can move on to the power production phase.
    """},
    {"role": "user", "content": """
    ## What you need to do is:
    * Identify all moments from the weather forecast where the wind is very strong and could damage the turbine blades. At those times, secure the turbine (appropriate blade pitch and correct operating mode).
    * Determine the point at which it is possible to generate the missing energy, and set the optimal rotor blade pitch and the correct operating mode to enable power production.
    * Every configuration sent to the API must be digitally signed. However, we have a code generator that will create these for you—unlockCodeGenerator—and you must send the generated codes along with the configuration.
    * Save the configuration using config.
    * Finally, send an action named done, which will verify if your configuration is correct.
    """},
    {"role": "user", "content": """
    ## Additional Notes
    * **Asynchronous Operations:** Most functions operate asynchronously. First, you add a task to the queue, and then you retrieve the result via the `getResult` action. Responses arrive in a random order.
    * **Windstorm Definition:** A windstorm is defined as wind that exceeds the turbine's durability threshold.
    * **Turbine Safety:** During a windstorm, the turbine should not provide resistance and must not produce electricity.
    * **Final Verification:** Before sending the final `done` action, you must perform a turbine test via `turbinecheck`.
    * **Security Requirements:** Each configuration point must include a valid `unlockCode` obtained from the `unlockCodeGenerator` function.
    """},
    {"role": "user", "content": """
    ## Important
    * generate only 4 configuration points - you only need one time window to generate power
    """},
    {"role": "user", "content": """
    ## Prefetched data
    * session is already started - do not call start again
    * reports for weather, turbinecheck, powerplantcheck, and documentation were requested for you - all attached in data object.
    * return only JSON array of configuration points without additional codes and unlock codes in format:
    {
        "startDate": "YYYY-MM-DD",
        "startHour": "HH:00:00",
        "pitchAngle": int,
        "turbineMode": "production" or "idle",
        "windMs": int
    }
    """},
    {"role": "user", "content": json.dumps(data)}
]

logger.info("[time] Starting main loop - elpased time: %d", elpased())

while True:
    content = call_model(
        # model="openai/gpt-5.4",
        messages = messages,
        tools=[start_tool, get_tool, get_result_tool, config_tool, unlock_code_generator_tool],
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

            if function["name"] == "start":
                content = start()
            elif function["name"] == "get":
                content = get(arguments["param"])
            elif function["name"] == "get_result":
                content = get_result()
            elif function["name"] == "config":
                content = config(
                    start_date=arguments["startDate"],
                    start_hour=arguments["startHour"],
                    pitch_angle=arguments["pitchAngle"],
                    turbine_mode=arguments["turbineMode"],
                    unlock_code=arguments["unlockCode"],
                )
            elif function["name"] == "unlockCodeGenerator":
                content = unlock_code_generator(
                    start_date=arguments["startDate"],
                    start_hour=arguments["startHour"],
                    wind_ms=arguments["windMs"],
                    pitch_angle=arguments["pitchAngle"],
                )
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


logger.info("[time] Finished main loop - elpased time: %d", elpased())

configuration_points = json.loads(content["content"])

logger.info("Loading unlock codes for configuration points - elpased time: %d", elpased())
unlock_codes_count = 0
for config_point in configuration_points:
    thread = threading.Thread(target=unlock_code_generator, kwargs={
        "start_date": config_point["startDate"],
        "start_hour": config_point["startHour"],
        "wind_ms": config_point["windMs"],
        "pitch_angle": config_point["pitchAngle"],
    })
    thread.start()
    unlock_codes_count = unlock_codes_count + 1
logger.info("Unlock code generator threads started: %d - elpased: %s", unlock_codes_count, elpased())

logger.info("Fetching unlock codes from queue - elpased time: %d", elpased())
unlock_codes = []
for i in range(40):
    logger.info("[getResult] Elpased time %d, unlock codes retrieved: %d", elpased(), len(unlock_codes))

    result = get_result()
    if "sourceFunction" in result and result["sourceFunction"] == "unlockCodeGenerator":
        unlock_codes.append(result)
        continue

    wait(1)
    if len(unlock_codes) == unlock_codes_count:
        break

# logger.info("Example unlock codes: %s", json.dumps(unlock_codes, indent=2))

logger.info("Assigning unlock codes to configuration points...")
for config_point in configuration_points:
    for code in unlock_codes:
        code_params = code["signedParams"]
        if code_params["startDate"] == config_point["startDate"]and code_params["startHour"] == config_point["startHour"] and float(code_params["pitchAngle"]) == float(config_point["pitchAngle"]) and float(code_params["windMs"]) == float(config_point["windMs"]):
            config_point["unlockCode"] = code["unlockCode"]

    if "unlockCode" not in config_point:
        raise ValueError("No matching unlock code found for config point: %s" % json.dumps(config_point))

logger.info("Sending configuration points - elpased time: %d", elpased())
for config_point in configuration_points:
    result = config(
        start_date=config_point["startDate"],
        start_hour=config_point["startHour"],
        pitch_angle=config_point["pitchAngle"],
        turbine_mode=config_point["turbineMode"],
        unlock_code=config_point["unlockCode"],
    )
    logger.info("Config result: %s", json.dumps(result))

logger.info("Sending done action - elpased time: %d", elpased())
result = done()
logger.info("Done result: %s", json.dumps(result))
