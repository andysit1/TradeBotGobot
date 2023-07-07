from fastapi import FastAPI, BackgroundTasks
import logging
import steam
import asyncio
import os
from app.logic import BookKeeper, Game
from steam.utils import DateTime
import time
import json
import requests

logger = logging.getLogger('steam')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='steam.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
identity = os.getenv("IDENTITY_SECRET")
secret = os.getenv("SHARED_SECRET")


app = FastAPI()
#only purpose to pull data on users...
rust_instance = steam.Game(id=252490, name="Rust")


keeper = BookKeeper()

def untilTrades(tradeid: str, roomid: str, api_key: str, trade_type: int):
  running = True
  url = "https://api.steampowered.com/IEconService/GetTradeOffers/v1"
  params = {
    "key": api_key,
    "active_only": "true",
    "get_sent_offers": "true",
    "get_received_offers": "true",
    "get_descriptions": "true",
    "cursor": "0",
    "language": "english",
    "time_historical_cutoff": int(DateTime.now().timestamp())
  }

  count = 0

  while running:
    data = requests.get(url=url, params=params)
    d = json.loads(data.text)
    tradeoffer = d['response']['trade_offers_sent']
    print("Trying...")
    for trade in tradeoffer:
      if trade.get("message") == tradeid:
        state = trade.get("trade_offer_state")
        print("STATE", state)

        if state == 3:
          print("FOUND THE TRADE!!!!")
          url = "http://143.110.208.76:80/game/accepted/{}".format(roomid)
          print(url)
          requests.post(url=url)
          return

        if state == 2:
            tradeofferid = trade.get("tradeofferid")
            print("Found tradeid", tradeofferid)
            keeper.setTradeID(tradeid=tradeofferid, roomid=roomid)
            keeper.printInfo()

        if state == 6:
           print("Trade was canceled, stop checking...")
           return

    time.sleep(5)
    count += 5

    #if trade_type is 1 it means we want to check if count is 90 to send a post..
    if trade_type == 1 and count == 90:
      print("canceling trade...")
      url = "http://143.110.208.76:80/game/canceled/{}".format(roomid)
      print(url)
      requests.post(url=url)
      return



class MyClient(steam.Client):
    async def on_ready(self):
        print("------------")
        print("Logged in as")
        print("Username:", self.user)
        print("ID:", self.user.id64)
        print("Friends:", len(await self.user.friends()))
        print("------------")

client = MyClient()

async def getRoomID():
  url = "https://www.random.org/strings/?num=1&len=15&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain&rnd=new"
  response = requests.get(url)
  if response.status_code == 200:
    return response.text.strip()
  else:
    print("error getting string")


@app.on_event("startup")
async def startup_event():
  print("starting")
  asyncio.create_task(client.start(username="bipslegal", password="NEu85DPV", shared_secret="Uu6U8XkRdHz71Jg53lXNw5mdBpQ=", identity_secret="XM/OqUndEySZW/7/z+ufiiTnYic="))

@app.get('/')
def root():
    return {"message":"hello world"}

@app.get('/user/{userid}')
async def userInfo(userid: str):
    user = steam.SteamID(int(userid))
    userRepresentation = await client.fetch_user(user)

    payload = {
        "name" : userRepresentation.name,
        "avatar" : userRepresentation.avatar_url,
    }

    return {"message":userid, "payload" : payload}

@app.post('/trade/{userid}')
async def tradeItem(userid: str, game : Game, background: BackgroundTasks):

    user = steam.SteamID(int(userid))
    token = game.token
    items = game.items
    roomid = game.roomid

    print(user, token, items,type(items), roomid)
    secur_code = await getRoomID()

    if game.event == "GET":
        userRepresentation = await client.fetch_user(user)
        userInventory: steam.Inventory = await userRepresentation.inventory(game=rust_instance)

        send = []
        for item in items:
            print(item)
            curItem = userInventory.get_item(item[0])
            if curItem:
                send.append(curItem)
            else:
                print("ERROR HERE", item[0])

        trade = steam.TradeOffer(token=token, items_to_send=None, items_to_receive=send, message=secur_code)
        await userRepresentation.send(trade=trade)

        background.add_task(untilTrades, secur_code, roomid, client.http.api_key, game.trade_type)

    if game.event == "SEND":
        userRepresentation = await client.fetch_user(user)
        myInventory = await client.user.inventory(game=rust_instance)
        send = []
        for item in items:
            print(item)
            curItem = myInventory.get_item(item[0])
            if curItem:
                send.append(curItem)
            else:
                print("ERROR HERE", item[0])

        trade = steam.TradeOffer(token=token, items_to_send=send, items_to_receive=None, message=secur_code)
        await userRepresentation.send(trade=trade)

    #infinitely chekcs for the security code in trades...

#cancels the trade based on the room
@app.post('/trade_cancel/{roomid}')
async def cancelTrade(roomid: str):
    print(roomid, type(roomid))
    tradeid = keeper.user_trade[roomid]
    print("tradeid", tradeid)
    trade = client.get_trade(int(tradeid))

    if trade:
        print("Canceling")
        await trade.cancel()

@app.post('/tradeHistory')
async def checkTradeHistory():
    trades = client.trade_history(limit=5)
    trade_list = await trades.flatten()
    print(trade_list)

@app.post("/transfer")
async def transfer_all():
    user = steam.SteamID(76561198309967258)
    userRepresentation = await client.fetch_user(user)

    userInventory: steam.Inventory = await client.user.inventory(game=rust_instance)
    print(userInventory.items)

    try:
        trade = steam.TradeOffer(token="MM6cAEpF", items_to_send=userInventory.items, items_to_receive=None)
        await userRepresentation.send(trade=trade)
    except:
        print("inventory.items is not right...")

@app.on_event("shutdown")
async def closingbot():
    await client.close()


# steam.Client.trade_history

