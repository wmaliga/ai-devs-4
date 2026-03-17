import base64

import requests


def get_base64_image(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    data = base64.b64encode(response.content).decode('utf-8')
    return f"data:image/png;base64,{data}"
