from fastapi import FastAPI

app = FastAPI()

@app.post("/lampu/{condition}")
async def lamp_configuration(condition):
    try:
        condition_conv = condition_converter(condition)
    except Exception as e:
        return {
            "message": str(e)
        }

    return {
        "message": f"lamp successfully turn {condition}"
    }


def condition_converter(condition):
    if condition == "on":
        return True
    
    if condition == "off":
        return False
    
    raise Exception("condition is not valid")