import Tkinter as tk
import ttk
import tkFileDialog
import pandas as pd
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.enums import *
import numpy as np
from datetime import datetime
from time import sleep
from tkinter import messagebox

def round_decimal(num, decimal):
    if decimal > 0:
        x = np.round(num/decimal, 0)*decimal
    else:
        x = np.round(num, 8)
    return '{0:.8f}'.format(x).rstrip('0').rstrip('.')



class BalanceGUI(tk.Frame):
    def __init__(self, parent, coins):
        tk.Frame.__init__(self, parent)
        parent.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.parent = parent
        parent.deiconify()
        self.coins = coins
        self.coins_base = coins
        self.lock = False

        #portfolio display
        self.portfolio_view = tk.LabelFrame(parent, text='Portfolio')
        self.portfolio_view.grid(row=0,column=0, sticky=tk.E+tk.W)
        self.portfolio = ttk.Treeview(self.portfolio_view)
        self.portfolio['columns']=('Stored','Exchange', 'Target','Actual', 'Bid', 'Ask', 'Action', 'Status')
        for label in self.portfolio['columns']:
            if label == 'Action' or label == 'Status':
                self.portfolio.column(label, width=250)
            else:
                self.portfolio.column(label, width=100)
            self.portfolio.heading(label, text=label)
        self.portfolio.grid(row=0,column=0)

        #options display
        self.controls_view = tk.LabelFrame(parent, text='Controls')
        self.controls_view.grid(row=1, column=0, sticky=tk.E+tk.W)

        key_label = tk.Label(self.controls_view, text='API Key')
        key_label.grid(row=0, column=0,sticky=tk.E+tk.W)
        secret_label = tk.Label(self.controls_view, text='API Secret')
        secret_label.grid(row=0, column=2,sticky=tk.E+tk.W)
        self.key_entry = tk.Entry(self.controls_view)
        self.key_entry.grid(row=0, column=1,sticky=tk.E+tk.W)
        self.secret_entry = tk.Entry(self.controls_view, show='*')
        self.secret_entry.grid(row=0, column=3,sticky=tk.E+tk.W)
        self.login = tk.Button(self.controls_view, text='Login', command = self.api_enter)
        self.login.grid(row=0, column=4, sticky=tk.E+tk.W)

        
        self.refresh_button = tk.Button(self.controls_view, text='Refresh', command=self.populate_portfolio, state='disabled')
        self.refresh_button.grid(row=1,column=2, sticky=tk.E+tk.W)
        self.dryrun_button = tk.Button(self.controls_view, text='Dry Run', command=self.dryrun, state='disabled')
        self.dryrun_button.grid(row=1,column=3, sticky=tk.E+tk.W)
        self.rebalance_button = tk.Button(self.controls_view, text='Rebalance', command=self.rebalance, state='disabled')
        self.rebalance_button.grid(row=1,column=4, sticky=tk.E+tk.W)

        self.ordertype = tk.StringVar()
        self.ordertype.set('Market-Limit')
        self.orderopt = tk.OptionMenu(self.controls_view, self.ordertype, 'Market', 'Market Limit')
        self.orderopt.grid(row=1, column=0, stick=tk.E+tk.W)
        self.orderopt['state'] = 'disabled'

        self.trade_currency = tk.StringVar()
        self.trade_currency.set('BTC')
        self.trade_currency_opt = tk.OptionMenu(self.controls_view, self.trade_currency, 'BTC', command=self.currency_change)
        self.trade_currency_opt.grid(row=1, column=1, stick=tk.E+tk.W)
        self.trade_currency_opt['state'] = 'disabled'

        self.test_socket = tk.Button(self.controls_view, text='Test Sockets', command=self.test_sockets)
        self.test_socket.grid(row=0, column=5, sticky=tk.E+tk.W)
        self.test_socket = tk.Button(self.controls_view, text='Close Sockets', command=self.close_sockets)
        self.test_socket.grid(row=1, column=5, sticky=tk.E+tk.W)
        
        

        #streaming display
        self.stream_view = tk.LabelFrame(parent, text='Current State')
        self.stream_view.grid(row=2, column=0, sticky=tk.E+tk.W)
        self.commands = tk.StringVar()
        self.commands.set('{0}: Ready'.format(datetime.today().replace(microsecond=0)))
        self.stream = tk.Label(self.stream_view, textvariable = self.commands, justify=tk.LEFT)
        self.stream.grid(row=0, column=0, sticky=tk.E+tk.W)

    def on_closing(self):
        self.bm.close()
        self.parent.destroy()
        
    def test_sockets(self):
        self.bm = BinanceSocketManager(self.client)
        self.bm.start()
        self.test_socket = self.bm.start_symbol_ticker_socket('ETHBTC', self.process_message)

    def close_sockets(self):
        self.bm.stop_socket(self.test_socket)
        self.bm.close()
    
    def process_message(self, msg):
        print('bid: {0}\task{1}'.format(msg['b'], msg['a']))
    
    def api_enter(self):
        api_key = self.key_entry.get()
        self.key_entry.delete(0,'end')
        api_secret = self.secret_entry.get()
        self.secret_entry.delete(0,'end')

        
        self.key_entry['state'] = 'disabled'
        self.secret_entry['state'] = 'disabled'
        self.login['state'] = 'disabled'
        self.refresh_button['state'] = 'normal'
        self.dryrun_button['state'] = 'normal'
        self.orderopt['state'] = 'normal'
        self.trade_currency_opt['state'] = 'normal'

        self.update_commands('{0}: Logging in'.format(datetime.today().replace(microsecond=0)))
        self.client = Client(api_key, api_secret)
        status = self.client.get_system_status()
        self.update_commands('{0}: System status: {1}'.format(datetime.today().replace(microsecond=0), status['msg']))
        
        self.populate_portfolio()

        self.start_websockets()
        
    def start_websockets(self):
        self.bm = BinanceSocketManager(self.client)
        self.bm.start()
        trade_currency = self.trade_currency.get()
        symbols = self.coins['symbol'].tolist()
        symbols.remove(trade_currency+trade_currency)

        self.sockets = {}
        for symbol in symbols:
            self.sockets[symbol] = self.bm.start_symbol_ticker_socket(symbol, self.update_price)
        self.sockets['user'] = self.bm.start_user_socket(self.update_user)

    def update_user(self, msg):
        print msg


    def update_price(self, msg):
        if not self.lock:
            coin = msg['s'][:-len(self.trade_currency.get())]
            ask = float(msg['a'])
            bid = float(msg['b'])
            
            self.portfolio.set(coin, column='Ask', value=round_decimal(ask,self.coins.loc[self.coins['coin'] == coin, 'ticksize'].values[0]))
            self.coins.loc[self.coins['coin'] == coin, 'askprice'] = ask
            
            
            
            self.portfolio.set(coin, column='Bid', value=round_decimal(bid,self.coins.loc[self.coins['coin'] == coin, 'ticksize'].values[0]))
            self.coins.loc[self.coins['coin'] == coin, 'bidprice'] = bid


            value = (self.coins.loc[self.coins['coin'] == coin, 'exchange_balance'].values[0] + self.coins.loc[self.coins['coin'] == coin, 'fixed_balance'].values[0])*ask
            self.coins.loc[self.coins['coin'] == coin, 'value'] = value

            self.total = np.sum(self.coins['value'])
            
            self.coins['actual'] = self.coins.apply(lambda row: 100.0*row.value/self.total, axis=1)
            for coin in self.coins['coin']:
                actual = self.coins.loc[self.coins['coin'] == coin, 'actual'].values[0]
                self.portfolio.set(coin, column='Actual', value='{0:.2f}%'.format(actual))
        else:
            print '{0} locked'.format(msg['s'])
        
    def update_commands(self, string):
        self.commands.set(self.commands.get() + '\n' + string)
        with open('binance_balance_log.log','a') as f:
            f.write('\n' + string)
                          
    def dryrun(self):
        self.lock = True
##        self.rebalance_button['state'] = 'normal'
##        self.populate_portfolio()
##        self.coins['difference'] = self.coins.apply(lambda row: (row.allocation - row.actual)/100.0 * self.total/row.price,axis=1)
##        trade_type = self.ordertype.get()
##        trade_currency = self.trade_currency.get()
##        for row in self.coins.itertuples():
##            coin = row.coin
##            dif = row.difference
##            qty = np.absolute(dif)
##            price = row.price
##            pair = coin+trade_currency
##            action = 'None'
##            if qty < row.minqty:
##                self.portfolio.set(coin, column='Status', value='Trade quantity too small')
##            elif qty > row.maxqty:
##                self.portfolio.set(coin, column='Status', value='Trade quantity too large')
##            elif qty * price < row.minnotional:
##                self.portfolio.set(coin, column='Status', value='Trade value too small')
##            elif pair == trade_currency+trade_currency:
##                self.portfolio.set(coin, column='Status', value='Ready')
##            else:
##                if dif < 0:
##                    side = SIDE_SELL
##                else:
##                    side = SIDE_BUY
##                action = '{0} {1} {2} @ {3} {4}/{2}'.format(side, round_decimal(qty, row.stepsize), coin, round_decimal(price, row.ticksize), trade_currency)
##                try:
##                    if trade_type == 'Market-Limit':
##                        order = self.client.create_test_order(symbol = pair,
##                                                             side = side,
##                                                             type = ORDER_TYPE_LIMIT,
##                                                             timeInForce = TIME_IN_FORCE_GTC,
##                                                             quantity = round_decimal(qty, row.stepsize),
##                                                             price = round_decimal(price, row.ticksize))
##                    elif trade_type == 'Market':
##                        order = self.client.create_test_order(symbol = pair,
##                                                             side = side,
##                                                             type = ORDER_TYPE_MARKET,
##                                                             quantity = round_decimal(qty, row.stepsize))                    
##                except Exception as e:
##                    self.portfolio.set(coin, column='Status', value=e)
##                else:
##                    self.portfolio.set(coin, column='Status', value='Trade Ready')
##            if coin == trade_currency:
##                action = 'Mediate Trades'
##            self.portfolio.set(coin, column='Action', value=action)
##            
        
    def currency_change(self, event):
        self.populate_portfolio()



    def populate_portfolio(self):
        self.coins = self.coins_base
        self.portfolio.delete(*self.portfolio.get_children())
        exchange_coins = []
        trade_currency = self.trade_currency.get()
        
        for coin in self.coins['coin']:
            pair = coin+trade_currency
            balance = self.client.get_asset_balance(asset=coin)
            if coin != trade_currency:
                price = float(self.client.get_symbol_ticker(symbol = pair)['price'])
                symbolinfo = self.client.get_symbol_info(symbol=pair)['filters']
                row = {'coin': coin, 'exchange_balance': float(balance['free']),
                   'minprice': float(symbolinfo[0]['minPrice']), 'maxprice': float(symbolinfo[0]['maxPrice']), 'ticksize': float(symbolinfo[0]['tickSize']),
                   'minqty': float(symbolinfo[1]['minQty']), 'maxqty': float(symbolinfo[1]['maxQty']), 'stepsize': float(symbolinfo[1]['stepSize']),                   
                   'minnotional': float(symbolinfo[2]['minNotional']), 'symbol': pair, 'askprice' : price, 'bidprice': price, 'price': price}
            else:
                fixed_balance = self.coins.loc[self.coins['coin'] == coin]['fixed_balance']
                row = {'coin': coin, 'exchange_balance': float(balance['free']),
                   'minprice': 0, 'maxprice': 0, 'ticksize': 0,
                   'minqty': 0, 'maxqty': 0, 'stepsize': 0,                   
                   'minnotional': 0, 'symbol': coin+coin, 'askprice' : 1.0, 'bidprice': 1.0, 'price': 1.0}
            exchange_coins.append(row)
        exchange_coins = pd.DataFrame(exchange_coins)
        self.coins = pd.merge(self.coins, exchange_coins, on='coin', how='outer')

        self.coins['value'] = self.coins.apply(lambda row: row.price*(row.exchange_balance + row.fixed_balance), axis=1)
        self.total = np.sum(self.coins['value'])
        self.coins['actual'] = self.coins.apply(lambda row: 100.0*row.value/self.total, axis=1)

        
        i = 0
        for row in self.coins.itertuples():
            self.portfolio.insert("" , i, iid=row.coin, text=row.coin,
                                  values=(round_decimal(row.fixed_balance, row.stepsize), round_decimal(row.exchange_balance, row.stepsize),
                                          '{0} %'.format(row.allocation), '{0:.2f} %'.format(row.actual), round_decimal(row.price, row.ticksize),round_decimal(row.price, row.ticksize),'','Waiting'))
            i += 1
        
    def rebalance(self):
        self.rebalance_button['state'] = 'disabled'
    
def main():
    root = tk.Tk()
    root.withdraw()
    portfolio = tkFileDialog.askopenfilename(initialdir='C:/Users/kbrig035/Documents/GitHub/BinanceBalance/')
    coins = pd.read_csv(portfolio)
    BalanceGUI(root, coins).grid(row=0, column=0)
    root.wm_title('BinanceBalance')
    root.mainloop()

if __name__=="__main__":
    main()
