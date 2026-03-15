import urllib.request
import urllib.error
import urllib.parse
import json

TWIN_URL = "http://localhost:8080/api/logschedule/neworder"

RED_OUTPUT = "69b6e349b1c3a15583168566"
BLUE_OUTPUT = "69b6e34fb1c3a155831686e9"
WHITE_OUTPUT = "69b6e357b1c3a15583168869"
FAILED_OUTPUT = "69b6e9afaecddb203c2c383f"

RED_TARGET = "69b6ec0497e93d0906e0d15c"
BLUE_TARGET = RED_TARGET
WHITE_TARGET = RED_TARGET


def PartPassed(partColor: str):
    if partColor == "RED":
        SendMaterialRequest("RED", RED_OUTPUT, RED_TARGET)
    elif partColor == "BLUE":
        SendMaterialRequest("BLUE", BLUE_OUTPUT, BLUE_TARGET)
    elif partColor == "WHITE":
        SendMaterialRequest("WHITE", WHITE_OUTPUT, WHITE_TARGET)
    else:
        print("Undefined")


def PartFailed():
    print("Failed part")


def SendMaterialRequest(materialType: str, sourceWhUnit: str, targetWhUnit: str):
    payload = {
        "data": json.dumps({
            "name": "From MQTT",
            "what_material": materialType,
            "from": sourceWhUnit,
            "to": targetWhUnit,
            "pickupMode": 1,
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
