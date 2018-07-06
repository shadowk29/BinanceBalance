This project still requires testing. I don't recommend using it yet.

This is a simple cryptocurrency portfolio rebalancing app that allows you to maintain a fixed percentage allocation of any coins that have a BTC pairing on Binance. It uses the python-binance (https://github.com/sammchardy/python-binance) API to interact with Binance in order to pull balances and execute trades. 

This app runs entirely locally, meaning that your API keys do not need to be stored on a server anywhere. It allows for LIMIT orders (at market price) so that trading in low-volume coins is relatively safe when rebalancing automatically, though be aware that LIMIT orders are not guaranteed to get filled and the app currently does not cancel orders automatically. 

To run, there must be a configuration file present in the same directory as the code/executable called allocations.csv. This file lists all of the coins you wish the bot to handle, the amount you have in cold storage off the exchange, and the desired allocation percentage. An example is below:

coin,fixed_balance,allocation

BTC,0.5,13

ETH,2,13

XLM,1000,10

LTC,3,10

ZRX,200,10

THETA,1000,7

NANO,20,7

IOTA,50,5

BNB,2,5

NEO,1,5

OMG,10,5

XMR,3,5

XRP,50,5

Coins which are not listed in this file will be ignored even if you hold them on Binance. 

When run, you will be asked to enter your API key/secret. These are not stored anywhere except in RAM while the program is running. 

Automating trades will simply result in continuous trading until terminated by the user or a bad connection.



