import asyncio
import aiohttp
import os
import joblib
import requests
import json

current_dir = os.getcwd()

#async调取多个instrument
async def send_post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.json()

async def main(url, data_list):
    async with aiohttp.ClientSession() as session:
        tasks = [send_post_request(session, url, data) for data in data_list]
        responses = await asyncio.gather(*tasks)
        session.close()
        return responses
#初始化
username = 'UBIQ_TEAM359'
password = 'eeKvoJiLv'
domain_name = "https://trading.competition.ubiquant.com"
session = requests.Session()
url = domain_name + "/api/Login"
data = {
    "user": username,
    "password": password
}
response = session.post(url, data=json.dumps(data)).json()
token_ub = response["token_ub"]
#获取instruments
url = domain_name + "/api/TradeAPI/GetInstrumentInfo"
data = {
    "token_ub": token_ub,
}
response = session.post(url, data=json.dumps(data)).json()

instruments = []
for instrument in response["instruments"]:
    instruments.append(instrument["instrument_name"])
#获取数据
url = domain_name + "/api/TradeAPI/GetLimitOrderBook"
data_list = [{"token_ub": token_ub, "instrument": instrument} for instrument in instruments]

responses_list = []
while True:
    
    responses = asyncio.run(main(url, data_list))#if error, use 'responses = await main(url, data_list)'
    responses_list.append(responses)
    
    if (responses[-1]['status']!='Success'):
        responses_list.pop(-1)
        filepath = os.path.join(current_dir, 'data.pkl')
        if os.path.exists(filepath):
            os.remove(filepath)
        joblib.dump(responses_list, filepath)
    
