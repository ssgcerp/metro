import requests
import json
import random

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

session = requests.Session()
def json_rpc(endpoint, params):
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": random.randint(0, 1000000),
    }
    headers = {"Content-Type": "application/json"}
    response = session.post(f"{url}{endpoint}", data=json.dumps(data), headers=headers)
    return response.json()

result = json_rpc("/web/session/authenticate", {"db": db, "login": username, "password": password})
uid = result['result']['uid']

# Call action_post on payment 1456 (new BNK7/2025/12/0010)
res = json_rpc("/web/dataset/call_kw", {
    "model": "account.payment",
    "method": "action_post",
    "args": [[1456]],
    "kwargs": {}
})
print("Result of action_post:", json.dumps(res, indent=2))
