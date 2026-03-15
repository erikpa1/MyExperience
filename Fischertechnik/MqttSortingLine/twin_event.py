import json
import time

import urllib.request
import urllib.error
import urllib.parse

from config import *


def PartPassed(partColor: str):
    if partColor == "RED":
        SendMaterialRequest("000000000000000000000001", "RED", RED_OUTPUT, RED_TARGET)
    elif partColor == "BLUE":
        SendMaterialRequest("000000000000000000000002", "BLUE", BLUE_OUTPUT, BLUE_TARGET)
    elif partColor == "WHITE":
        SendMaterialRequest("000000000000000000000003", "WHITE", WHITE_OUTPUT, WHITE_TARGET)
    else:
        print("Undefined")


def PartFailed():
    print("Failed part")


def SendMaterialRequest(muUid: str, materialType: str, sourceWhUnit: str, targetWhUnit: str):


    payload = {
        "muConfig": json.dumps({
            "created": True
        }),
        "data": json.dumps({
            "name": "From MQTT",
            "what": muUid,
            "what_material": materialType,
            "from": sourceWhUnit,
            "to": targetWhUnit,
            "pickupMode": 0,
            "deadline": int(time.time() * 1000) + 1000 * 60 * 5,
        })
    }

    data = urllib.parse.urlencode(payload).encode("utf-8")

    req = urllib.request.Request(
        TWIN_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            print(f"Status: {status}")
            print(f"Response: {body}")

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")

    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
