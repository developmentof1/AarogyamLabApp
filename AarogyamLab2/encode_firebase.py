import base64

with open("aarogyamlab-e37e4-firebase-adminsdk-fbsvc-aeb8d59129.json", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
    print(b64)
