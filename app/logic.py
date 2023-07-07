from pydantic import BaseModel
from typing import Dict, List, Optional
import requests
from datetime import datetime
import time
import json
from steam.utils import DateTime
import steam
#PURPSOE
#store games into system to know whne to send items back...

class Game(BaseModel):
  event : str
  roomid : str
  items : list
  trade_type : int #0 is creating 1 is joinning
  token : Optional[str]
  tradeid : Optional[str]

class GameList(BaseModel):
  games : Dict[str, List[Game]]

class Item(BaseModel):
  items : List[str]

class BookKeeper():
  def __init__(self):
    self.user_trade = {}
    self.glist = GameList(games={})

  def store_trade(self, userid: str, trade: steam.TradeOffer):
    self.user_trade[userid] = trade

# this function is called when the trades are sent...
  def store(self, user: str, game : Game):
    games = self.glist.games.get(user)

    #no games made yet
    if not games:
      self.glist.games[user] = [game]

    #if user has a game existing make a new game listing...
    if games:
      self.glist.games[user].append(game)

  def setTradeID(self, tradeid: str, roomid:str):
    self.user_trade[roomid] = tradeid


  # this function should be called when trade accepted to find a match...
  #returns the match closest to time created...

  def printInfo(self):
    print(self.user_trade)

  async def cancelTrade(self, steamid:str, roomid: str, api_key: str):
    games = self.glist.games.get(steamid)
    url = "https://api.steampowered.com/IEconService/CancelTradeOffer/v1/"
    tradeid = None
    for game in games:
      #finds the roomid and sets that room as the tradeid for game
      if game.roomid == roomid:
        tradeid = game.tradeid

    if tradeid:
      params = {
        "key" : api_key,
        "tradeofferid" : tradeid
      }
      requests.post(url=url, params=params)
      print("Sent trade cancel request...")
    else:
      print("No roomid exist in this data. Error must have erroed...")



#pings tradeoffers in steam to check for the tradeoffers


  #if the trade type is 0 it should appear is there profile page and give them the option to cancel.


    #if trade_type is 1 it means we want to check if count is 90 to send a post..
