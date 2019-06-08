
import tkinter as tk
from tkinter import ttk
from tkinter import Tk, Label, Button, messagebox
from tkinter import *
import time
import threading
import random
import multiprocessing
from multiprocessing import Pool, Process, Queue 
import time
import pandas as pd
from pandas import DataFrame
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.enums import *
from binance.exceptions import *
import numpy as np
from datetime import datetime
from twisted.internet import reactor
import os.path
import configparser
from collections import deque
from scipy.signal import detrend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button, RadioButtons

received = 0
processed = 0
lastQsize = 0
processIncomingFlag = False
queue = multiprocessing.Queue()
maxThreads = 2
client = None
t1 = None


def round_decimal(num, decimal):
    '''
    Round a given floating point down number 'num' to the nearest integer
    multiple of another floating point number 'decimal' smaller than
    'num' and return it as a string with up to 8 decimal places,
    dropping any trailing zeros.
    '''
    if decimal > 0:
     x = int(num/decimal)*decimal
    else:
        x = np.round(num, 8)
    return '{0:.8f}'.format(x).rstrip('.')


class TrendLine:
    def __init__(self, window, dt):
        self.t = deque()
        self.y = deque()
        self.window = window
        self.dt = dt
        self.trend = 0

    def append(self,t,y):
        if self.t and t - self.t[0] > self.window:
            self.t.popleft()
            self.y.popleft()
        self.t.append(t)
        self.y.append(y)

    def trend(self):
        p = np.polyfit(self.t, self.y, 2)
        localstd = self.local_stdev(self.t,self.y,self.dt)
        dy = p[0]*(2*self.t[-1]*self.dt + self.dt**2) + p[1]*self.dt
        if np.absolute(dy) - localstd > 0:
            if dy > 0:
                self.trend = 1
            else:
                self.trend = -1
        else:
            self.trend = 0
    
    def local_stdev(self):
        start = self.t[0]
        end = self.t[-1] - dt
        t = np.array(self.t)
        y = np.array(self.y)
        localstd = []
        while start < end:
            inds = [(t >= start) * (t < start + self.dt)]
            localy = y[inds]
            localstd.append(np.std(localy))
            start += dt
        return np.min(localstd)

class GuiPart:
    def __init__(self, master, queue):
        master.protocol('WM_DELETE_WINDOW', self.on_closing)
        #self.queue = queue
        self.master = master
        self.received = 0
        self.trade_coin_Locked = 0
        self.trade_coin_Free = 0
        self.trade_coin_Balance = 0
        self.parent = master
        # Set up the GUI
        #pending on your specific needs
        ##console = tk.Button(master, text='Done', command=self.hello)
        #console.pack(  )

        portfolio = 'allocation.csv'
        coins = pd.read_csv(portfolio)

    
        #self.queue = queue
        self.coins = coins
        self.coins_base = coins
        self.trade_currency = "BTC"
        self.min_trade_value = 0.0045
        parent = master

        self.trades_placed = 0
        self.trades_completed = 0
        self.trades = []
        self.headers = self.column_headers()
        self.read_config()

        
        self.initalize_records()
        
       

         #options display
        self.controls_view = tk.LabelFrame(parent, text='Controls')
        for i in range(4):
            self.controls_view.columnconfigure(i,weight=1, uniform='controls')
        self.controls_view.grid(row=1, column=0, sticky=tk.E + tk.W + tk.N + tk.S)
        
        self.key_label = tk.Label(self.controls_view, text='API Key', relief='ridge')
        self.key_label.grid(row=0, column=0,sticky=tk.E + tk.W)
        
        self.secret_label = tk.Label(self.controls_view, text='API Secret', relief='ridge')
        self.secret_label.grid(row=1, column=0,sticky=tk.E + tk.W )
        
        k = tk.StringVar( value='')
        s = tk.StringVar( value='')

        self.key_entry = tk.Entry(self.controls_view, show='*')
        self.key_entry.grid(row=0, column=1, columnspan=2,sticky=tk.E + tk.W)
        
        self.secret_entry = tk.Entry(self.controls_view, show='*')
        self.secret_entry.grid(row=1, column=1, columnspan=2, sticky=tk.E + tk.W)
        
        api_key = self.key_entry.get()
        self.key_entry.delete(0,'end')
        api_secret = self.secret_entry.get()
        self.secret_entry.delete(0,'end')

        self.client = Client(api_key, api_secret)

        self.key_entry = tk.Entry(self.controls_view,textvariable=k)
        self.key_entry.grid(row=0, column=1, columnspan=2,sticky=tk.E + tk.W)
        
        self.secret_entry = tk.Entry(self.controls_view, textvariable=s) 
        self.secret_entry.grid(row=1, column=1, columnspan=2, sticky=tk.E + tk.W)
         
        self.login = tk.Button(self.controls_view,
                               text='Login',
                               command = self.api_enter)
        self.login.grid(row=0, column=3, rowspan=2, sticky=tk.E + tk.W + tk.N+tk.S)

    
        self.hellobtn = tk.Button(self.controls_view,
                               text='click me',
                               command = self.hello)
        self.hellobtn.grid(row=0, column=4, rowspan=2, sticky=tk.E + tk.W + tk.N+tk.S)

         #portfolio display
        self.portfolio_view = tk.LabelFrame(master, text='Portfolio')
        self.portfolio_view.grid(row=0, column=0, columnspan=2, sticky=tk.E + tk.W + tk.N + tk.S)

        
        self.portfolio = ttk.Treeview(self.portfolio_view, height = 20, selectmode = 'extended')
        
        self.portfolio['columns']=('Stored',
                                   'Exchange',
                                   'Locked',
                                   'Target',
                                   'Actual',
                                   'Bid',
                                   'Ask',
                                   'Action',
                                   'Status',
                                   'Event'
                                   )
        for label in self.portfolio['columns']:
            if label == 'Status' or label == 'Event':
                self.portfolio.column(label, width=200)
            elif label == '':
                self.portfolio.column(label, width=40)
            elif label == 'Action':
                self.portfolio.column(label, width=120)
            elif label == 'Actual':
                self.portfolio.column(label, width=60)
            elif label == 'Target':
                self.portfolio.column(label, width=60)
            else:
                self.portfolio.column(label, width=100)
            self.portfolio.heading(label, text=label)
        self.portfolio.grid(row=0,column=0)

        for i in range(2):
            master.columnconfigure(i,weight=0, uniform='parent')
    
     #Statistics display
        self.stats_view = tk.LabelFrame(parent, text='Statistics')
        self.stats_view.grid(row=1, column=1, sticky=tk.E + tk.W + tk.N + tk.S)
        
        self.stats_view.columnconfigure(0,weight=0, uniform='stats')
        self.stats_view.columnconfigure(1,weight=0, uniform='stats')
        self.stats_view.columnconfigure(2,weight=0, uniform='stats')
        self.stats_view.columnconfigure(3,weight=0, uniform='stats')

    
        self.trade_currency_value_label = tk.Label(self.stats_view, text=self.trade_currency + ' Value:', relief='ridge',width = 12)
        self.trade_currency_value_label.grid(row=0, column=0, sticky=tk.W + tk.E)
        self.trade_currency_value_string = tk.StringVar()
        self.trade_currency_value_string.set('0')
        self.trade_currency_value = tk.Label(self.stats_view, textvariable=self.trade_currency_value_string, width = 10)
        self.trade_currency_value.grid(row=0, column=1, sticky=tk.W)
        

        self.trade_currency_value_label_Start = tk.Label(self.stats_view, text=self.trade_currency + 'Start Value:', relief='ridge',width = 12)
        self.trade_currency_value_label_Start.grid(row=1, column=0, sticky=tk.W + tk.E)
        self.trade_currency_value_string_Start = tk.StringVar()
        self.trade_currency_value_string_Start.set('0')
        self.trade_currency_value_Start = tk.Label(self.stats_view, textvariable=self.trade_currency_value_string_Start,width = 10)
        self.trade_currency_value_Start.grid(row=1, column=1, sticky=tk.W)
        
        self.imbalance_label = tk.Label(self.stats_view, text='Imbalance:', relief='ridge',width = 12)
        self.imbalance_label.grid(row=2, column=0,  sticky=tk.W + tk.E)
        self.imbalance_string = tk.StringVar()
        self.imbalance_string.set('0%')
        self.imbalance_value = tk.Label(self.stats_view, textvariable=self.imbalance_string, width = 10)
        self.imbalance_value.grid(row=2, column=1, sticky=tk.W)
        
        self.status_label = tk.Label(self.stats_view, text='Status', relief='ridge',width = 12)
        self.status_label.grid(row=0, column=2,  sticky=tk.W)
        self.status_string = tk.StringVar()
        self.status_string.set('Idle')
        self.status_value = tk.Label(self.stats_view, textvariable=self.status_string, width = 40)
        self.status_value.grid(row=0, column=4, sticky=tk.W)

        self.messages_queued_label = tk.Label(self.stats_view, text='Stats', relief='ridge',width = 12)
        self.messages_queued_label.grid(row=1, column=2,  sticky=tk.W)
        self.messages_string = tk.StringVar()
        self.messages_string.set('Up to Date')
        self.messages_queued = tk.Label(self.stats_view, textvariable=self.messages_string, width = 40)
        self.messages_queued.grid(row=1, column=4, sticky=tk.W)
                
        self.trades_label = tk.Label(self.stats_view, text='Trades Placed:', relief='ridge',width = 12)
        self.trades_label.grid(row=2, column=2,  sticky=tk.W)
        self.trades_count = tk.IntVar()
        self.trades_count.set(0)
        self.trades_count_display = tk.Label(self.stats_view, textvariable=self.trades_count, width = 40)
        self.trades_count_display.grid(row=2, column=4, sticky=tk.W)

    def read_config(self):
        s_to_ms = 1000
        config = configparser.RawConfigParser(allow_no_value=False)
        config.read('config.ini')
        self.trade_currency = config.get('trades', 'trade_currency')
        if self.trade_currency != 'BTC':
            self.display_error('Config Error',
                               '{0} trading pairs are not supported yet, only BTC'.format(self.trade_currency),
                               quit_on_exit=True)
        self.rebalance_time = int(config.get('trades', 'rebalance_period')) * s_to_ms
        if self.rebalance_time <= 0:
            self.display_error('Config Error',
                               'Rebalance period must be a positive integer (seconds)',
                               quit_on_exit=True)
        self.min_trade_value = float(config.get('trades', 'min_trade_value'))
        if self.min_trade_value <= 0:
            self.min_trade_value = None
        self.trade_type = config.get('trades', 'trade_type')
        if self. trade_type != 'MARKET' and self.trade_type != 'LIMIT':
            self.display_error('Config Error',
                               '{0} is not a supported trade type. Use MARKET or LIMIT'.format(trade_type),
                               quit_on_exit=True)
        self.ignore_backlog = int(config.get('websockets', 'ignore_backlog'))
    

    def on_closing(self):
        ''' Check that all trades have executed
        before starting the save and exit process
        '''
        if self.trades_placed > 0 and self.trades_completed < self.trades_placed:
            if messagebox.askokcancel('Quit', 'Not all trades have completed. Quit anyway?'):
                self.save_and_quit()
        else:
            self.save_and_quit()

    def save_and_quit(self):
        '''
        If trades have been executed in the current session,
        save them to file. Stop all websockets and exit the GUI.
        '''
        if self.trades:
            df = pd.DataFrame(self.trades)
            if os.path.isfile('trade_history.csv'):
                with open('trade_history.csv','a') as f:
                    df.to_csv(f, sep=',', header=False, index=False)
            else:
                with open('trade_history.csv','w') as f:
                    df.to_csv(f, sep=',', header=True, index=False)
        for coin in self.coins['coin']:
            pair = coin+self.trade_currency
            self.records[pair].close()
        try:
            self.bm.close()
            reactor.stop()
            t1.join()
        except AttributeError:
            self.parent.destroy()
        else:
            self.parent.destroy()

    def exit_error(self):
        if self.quit_on_exit:
            self.top.destroy()
            self.save_and_quit()
        else:
            self.top.destroy()

    def display_error(self, title, error, quit_on_exit=False):
        self.quit_on_exit = quit_on_exit
        self.top = tk.Toplevel()
        self.top.title('Login Error')
        msg = tk.Message(self.top, text=error)
        msg.grid(row=0, column=0)
        button = tk.Button(self.top, text="Dismiss", command=self.exit_error)
        button.grid(row=1, column=0)
        self.top.attributes('-topmost', 'true')
        
    
    def api_enter(self):
        '''
        Log in to Binance with the provided credentials,
        update user portfolio and start listening to price and
        account update websockets.
        '''
        api_key = self.key_entry.get()
        self.key_entry.delete(0,'end')
        api_secret = self.secret_entry.get()
        self.secret_entry.delete(0,'end')
        
        try:
            self.client = Client(api_key, api_secret)
            status = self.client.get_system_status()
            
        except (BinanceRequestException,
                BinanceAPIException) as e:
            self.display_error('Login Error', e.message)
            self.messages_string.set('Login Error')
        else:
            try:
                self.populate_portfolio()
            except BinanceAPIException as e:
                self.display_error('API Error', e.message, quit_on_exit=True)
            else:
                self.status_string.set('Starting Websockets')
                queue.cancel_join_thread() 
                global t1
                t1 = multiprocessing.Process(target=GetSocketData,args=(self.client,queue,self.trade_currency,self.coins,))
                t1.start()
                self.status_string.set('Processing...')
                

    def populate_portfolio(self):
        '''
        Get all symbol info from Binance needed to
        populate user portfolio data and execute trades
        '''

        self.status_string.set('Populating Portfolio')
        self.coins = self.coins_base
        self.portfolio.delete(*self.portfolio.get_children())
        exchange_coins = []
        trade_currency = self.trade_currency
        self.trade_coin = trade_currency
        self.trendlines = {}

        #update the GUI context
        self.key_label.destroy()
        self.key_entry.destroy()
        self.secret_label.destroy()
        self.secret_entry.destroy()
        self.login.destroy()
        
        updatetext = tk.StringVar()
        updatetext.set('Initializing')
        self.progresslabel = tk.Label(self.controls_view, textvariable=updatetext)
        self.progresslabel.grid(row=1, column=0, columnspan=4, sticky=tk.E + tk.W)
        progress_var = tk.DoubleVar()
        progress = 0
        progress_var.set(progress)
        self.progressbar = ttk.Progressbar(self.controls_view, variable=progress_var, maximum=len(self.coins))
        self.progressbar.grid(row=0, column=0, columnspan=4, sticky=tk.E + tk.W)
        coin_count = len(self.coins)

        for coin in self.coins['coin']:
            
            self.progressbar.update()
            progress += 1
            progress_var.set(progress)
            updatetext.set('Fetching {0} account information'.format(coin))
            self.status_string.set('Populating Portfolio {0} - {1}'.format(progress,coin_count))
            self.progresslabel.update()
            if coin == 'USDT' or coin == 'USDC' or coin == 'TUSD':
                pair = trade_currency+coin
            else:
                pair = coin+trade_currency
            balance = self.client.get_asset_balance(asset=coin)
            if coin != trade_currency:
                price = float(self.client.get_symbol_ticker(symbol=pair)['price'])
                symbolinfo = self.client.get_symbol_info(symbol=pair)['filters']
                minvalue = float(symbolinfo[3]['minNotional'])
                if self.min_trade_value is not None:
                    minvalue = self.min_trade_value
                row = {'coin':              coin,
                       'exchange_balance':  float(balance['free']),
                       'locked_balance':    float(balance['locked']),
                       'minprice':          float(symbolinfo[0]['minPrice']),
                       'maxprice':          float(symbolinfo[0]['maxPrice']),
                       'ticksize':          float(symbolinfo[0]['tickSize']),
                       'minqty':            float(symbolinfo[2]['minQty']),
                       'maxqty':            float(symbolinfo[2]['maxQty']),
                       'stepsize':          float(symbolinfo[2]['stepSize']),                   
                       'minnotional':       minvalue,
                       'symbol':            pair,
                       'askprice' :         price,
                       'bidprice':          price,
                       'price':             price,
                       'last_placement':    None,
                       'last_execution':    None
                       }
                self.trendlines[coin] = TrendLine(1,1)
            else:
                fixed_balance = self.coins.loc[self.coins['coin'] == coin]['fixed_balance']
                self.trade_coin_Locked = float(balance['locked'])
                self.trade_coin_Free = float(balance['free'])
                self.trade_coin_Balance = self.trade_coin_Locked + self.trade_coin_Free
                #print (format(self.trade_coin_Balance, '.8f'))
                self.trade_coin_Balance = format(self.trade_coin_Balance, '.8f')
                row = {'coin':              coin,
                       'exchange_balance':  float(balance['free']),
                       'locked_balance':    float(balance['locked']),
                       'minprice':          0,
                       'maxprice':          0,
                       'ticksize':          0,
                       'minqty':            0,
                       'maxqty':            0,
                       'stepsize':          0,                   
                       'minnotional':       0,
                       'symbol':            coin+coin,
                       'askprice' :         1.0,
                       'bidprice':          1.0,
                       'price':             1.0,
                       'last_placement':    None,
                       'last_execution':    None
                       }
            exchange_coins.append(row)
        exchange_coins = pd.DataFrame(exchange_coins)
        self.coins = pd.merge(self.coins, exchange_coins, on='coin', how='outer')
        self.coins['value'] = self.coins.apply(lambda row: row.price * (row.exchange_balance +
                                                                        row.fixed_balance), axis=1)
        self.total = np.sum(self.coins['value'])
        self.coins['actual'] = self.coins.apply(lambda row: 100.0 * row.value/self.total, axis=1)
        self.update_status()
        i = 0
        for row in self.coins.itertuples():
            self.portfolio.insert('' ,
                                  i,
                                  iid=row.coin,
                                  text=row.coin,
                                  values=(row.fixed_balance,
                                          row.exchange_balance,
                                          row.locked_balance,
                                          '{0} %'.format(row.allocation),
                                          '{0:.2f} %'.format(row.actual),
                                          round_decimal(row.price, row.ticksize),
                                          round_decimal(row.price, row.ticksize),
                                          '',
                                          ''
                                          )
                                  )
            i += 1
        
        updatetext.set('Testing connection'.format(coin))
        self.dryrun()
        self.progressbar.destroy()
        self.progresslabel.destroy()
        
        self.automate=tk.BooleanVar()
        self.automate.set(False)
        self.automate_text = tk.StringVar()
        self.automate_text.set('Start Automation')
        self.toggle_automate = tk.Button(self.controls_view,
                                         textvariable=self.automate_text,
                                         command=lambda: self.automation(toggle=True))
        self.toggle_automate.grid(row=0, column=0, rowspan=2, columnspan=2, sticky=tk.E + tk.W + tk.N + tk.S)
        self.sell_button = tk.Button(self.controls_view,
                                     text='Execute Sells',
                                     command=self.execute_sells)
        self.sell_button.grid(row=0, column=2, columnspan=2, sticky=tk.E + tk.W)
        self.buy_button = tk.Button(self.controls_view,
                                    text='Execute Buys',
                                    command=self.execute_buys)
        self.buy_button.grid(row=1, column=2, columnspan=2, sticky=tk.E + tk.W)
        

    def initalize_records(self):

        self.records = dict()
        for coin in self.coins['coin']:
            pair = coin+self.trade_currency
            self.records[pair] = open(pair + '.csv','a+',1) #unbuffered
        
        '''   
        self.records = dict()
        for coin in self.coins['coin']:
            #if coin == 'USDT' or coin == 'USDC' or coin == 'TUSD':
            #    pair = self.trade_currency+coin
            #else:
            pair = coin+self.trade_currency#

            self.records[pair] = open(pair + '.csv','a+',1) #unbuffered
        '''

    def update_balance(self, msg):
        '''
        Update user balances internally and on the
        display whenever an account update message is received.
        '''
        balances = msg['B']
        coins = self.coins['coin'].values
        for balance in balances:
            coin = balance['a']
            
            if coin in coins:
                exchange_balance = float(balance['f']) + float(balance['l'])
                locked_balance = float(balance['l'])
                 
                if(coin == self.trade_coin):
                    self.trade_coin_Balance = exchange_balance
                    self.trade_coin_Locked = locked_balance

                self.portfolio.set(coin, column='Exchange', value=round_decimal(exchange_balance,self.coins.loc[self.coins['coin'] == coin]['stepsize'].values[0]))
                self.portfolio.set(coin, column='Locked', value=round_decimal(locked_balance,self.coins.loc[self.coins['coin'] == coin]['stepsize'].values[0]))
                self.coins.loc[self.coins['coin'] == coin, 'exchange_balance'] = exchange_balance
                self.coins.loc[self.coins['coin'] == coin, 'locked_balance'] = locked_balance
                ask = self.coins.loc[self.coins['coin'] == coin, 'askprice'].values[0]
                value = (self.coins.loc[self.coins['coin'] == coin, 'exchange_balance'].values[0] +
                         self.coins.loc[self.coins['coin'] == coin, 'fixed_balance'].values[0]) * ask
                self.coins.loc[self.coins['coin'] == coin, 'value'] = value

        self.total = np.sum(self.coins['value']) 
        self.coins['actual'] = self.coins.apply(lambda row: 100.0 * row.value / self.total, axis=1)
        for row in self.coins.itertuples():
            coin = row.coin
            actual = '{0:.2f}%'.format(self.coins.loc[self.coins['coin'] == coin, 'actual'].values[0])
            self.portfolio.set(coin, column='Actual', value=actual)
        self.update_actions()
        self.update_status()

    def hello(self):
            
        def listBoxSelectionChange(event):
            AddCoin(ListBoxSelectionString.get())
        
        def draw_Circle(self):

            #draw circle
            centre_circle = plt.Circle((0,0),0.70,fc='#eff0f0')
            self.fig = plt.gcf()
            self.fig.gca().add_artist(centre_circle)

        def apply_Fonts(texts,autotexts):
            
            for text in texts:
                text.set_color('black')
                text.set_fontsize(10)

            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontsize(10)

        #Draw the pie chart
        def Charting(self,portfolio_coins,fixed_balance,allocation):
           
            self.fig, self.ax = plt.subplots(figsize=(3, 3))
            self.allocation = allocation
            self.portfolio_coins = portfolio_coins
            
            #'Work around' which manually sets the charts canvas color manualy to be the same as the tkinter canvas color
            #so as to imitate a transparent background.
            self.fig.patch.set_facecolor('#eff0f0')

            #draw circle
            draw_Circle(self)
            
            #add piechart slice for the unallocated portfolio allocation
            self.unallocated = list()
            self.unallocated.append('Unallocated') 
            self.unallocatedVal = list()
            self.unallocatedVal.append(0)

            self.ax.pie(self.allocation + self.unallocatedVal ,labels=self.portfolio_coins+self.unallocated,autopct='%1.1f%%')

            bar1 = FigureCanvasTkAgg(self.fig, self.chartView)
            bar1.get_tk_widget().grid(row=0,column=0,padx=3)

        #Setup the new dialog window
        self.window = tk.Toplevel(self.master)
        self.window.geometry("1000x600") #Width x Height

        #Read the current portfolio allocations from allocation.csv
        #Do allocation.csv error checking
        portfolio = 'allocation.csv'
        allocations = pd.read_csv(portfolio)
        portfolio_coins = list()
        fixed_balance = list()
        allocation = list()

        self.Totals_String = StringVar(self.window)

        row = 0
        sliderValues = list()
        sliderId = list()
        self.blank = ''
        Default_Value = StringVar(self.window)
        Default_Value.set("0.0")
        
        Allocation_Frame = tk.LabelFrame(self.window, text='Portfolio Allocations')
        Allocation_Frame.grid(row=0, column=0, padx=10, sticky=tk.E + tk.W + tk.N + tk.S)
        

        #Add coin frame
        AddAsset_View = tk.LabelFrame(self.window, text='Add Coin to Portfoio')
        AddAsset_View.grid(row=0, column=1, padx=10, sticky=tk.E + tk.W + tk.N + tk.S)

        #Chart Frame
        self.chartView = tk.LabelFrame(self.window, text='Visualization')
        self.chartView.grid(row=0, column=2, padx=10, sticky=tk.E + tk.W + tk.N + tk.S)
                
        paddingX = 6

        tk.Label(Allocation_Frame, text='Coin', relief=tk.RIDGE, width=5 ).grid(row=0,column=1, padx=paddingX, sticky=tk.E + tk.W + tk.N + tk.S)
        tk.Label(Allocation_Frame, text='Fixed %', relief=tk.RIDGE).grid(row=0,column=2, padx=paddingX,  sticky=tk.E + tk.W + tk.N + tk.S)
        tk.Label(Allocation_Frame, text='Target Allocation %', relief=tk.RIDGE, width=7 ).grid(row=0,column=3, padx=paddingX, columnspan=2, sticky=tk.E + tk.W + tk.N + tk.S)
        tk.Label(Allocation_Frame, text='Remove', relief=tk.RIDGE, width=5 ).grid(row=0,column=5, padx=paddingX, sticky=tk.E + tk.W + tk.N + tk.S)
        
        Totals_Frame = tk.LabelFrame(self.window, text='Totals')
        Totals_Frame.grid(row=1, column=0, columnspan=6,sticky=tk.E + tk.W + tk.N + tk.S, padx=paddingX)
        tk.Label(Totals_Frame, textvariable=self.Totals_String,  width=60 ).grid(row=row, column=0, padx=paddingX)
        
        Markets = self.client.get_all_tickers()

        btcMarkets =[]
        for symbols in Markets:
            if symbols['symbol'][-3:] == 'BTC':
                coin = symbols['symbol'].replace('BTC','')
                btcMarkets.append(coin)

        ListBoxSelectionString= StringVar()

        listBox = ttk.Combobox(AddAsset_View, textvariable=ListBoxSelectionString, values=btcMarkets)
        listBox.grid(row=0,column=5,padx=3)
        listBox.bind("<<ComboboxSelected>>", listBoxSelectionChange)

        for line in allocations.itertuples():
             portfolio_coins.append(line.coin)
             fixed_balance.append(line.fixed_balance)
             allocation.append(line.allocation)
        
        
        self.WidgetList = list()
        
        def removeCoinB(coin):
             print('widgets ' + str(self.WidgetList))
             skip = False
             for i in range(0,len(self.WidgetList)):
                            
                            if skip == False:
                                if(self.WidgetList[i][1].cget("text") == coin):
                                    for item in self.WidgetList[i]:
                                        item.destroy()
                                            
                                    index = self.portfolio_coins.index(coin)

                                    self.portfolio_coins.remove(coin)                        
                                    self.allocation.pop(index)
                                    self.WidgetList.remove(self.WidgetList[i])
                                    sliderId.pop(index)
                                    skip = True
              
             for i in range(0,len(self.WidgetList)):           
                            self.WidgetList[i][0].config(text=i+1)
             
             for item in range(0,len(sliderId)):
                    sliderId[item].config(command=lambda value, name=item: sumAllocations(name, value))
                    
                               
                                                          
        for coin in portfolio_coins:
            widgets = list()
            sliderValues.append(StringVar())
            RowId    = tk.Label(Allocation_Frame, text=row+1,   relief=tk.RIDGE,  width=5)
            CoinId   = tk.Label(Allocation_Frame, text=coin,  relief=tk.RIDGE,  width=15)
            FixedId  = tk.Entry(Allocation_Frame, bg='white', relief=tk.SUNKEN, width=7, textvariable=Default_Value)
            EntryId  = tk.Entry(Allocation_Frame, bg='white', relief=tk.SUNKEN, width=7, textvariable=sliderValues[-1], state='disabled',)
            sliderid = tk.Scale(Allocation_Frame, variable=sliderValues[-1], showvalue=0, length=150, relief=tk.RIDGE, resolution=0.5, from_=0, to=100, orient='horizontal')
            sliderid.set(allocation[row])
            #update the command argument after the scale sliders default value has been set.
            sliderid.config(command=lambda value, name=row: sumAllocations(name, value))
            sliderId.append(sliderid)
            deleteBtn = tk.Button(Allocation_Frame,height=0,command=lambda coin=coin: removeCoinB(coin), width=13, text='Remove {0}'.format(coin), fg="red")
            
            RowId.grid(row=row+1,column=0, padx=paddingX)
            CoinId.grid(row=row+1,column=1, padx=paddingX)
            FixedId.grid(row=row+1,column=2, padx=paddingX)
            EntryId.grid(row=row+1,column=3, padx=paddingX)
            sliderid.grid(row=row+1,column=4, padx=paddingX)
            deleteBtn.grid(row=row+1,column=5, sticky=tk.E + tk.W, padx=paddingX, pady=3)

            row = row + 1

            widgets.append(RowId)
            widgets.append(CoinId)
            widgets.append(FixedId)
            widgets.append(EntryId)
            widgets.append(sliderid)
            widgets.append(deleteBtn)
            self.WidgetList.append(widgets)

        Charting(self,portfolio_coins,fixed_balance,allocation)
        
        #Update piechart with new values
        def update(val):
            def autopct_format(values):
                def my_format(pct):
                    y= list(map(float, values))
                    total = sum(y)
                    val = round(float(pct*total/100.0) * 2.0,1) / 2.0
                    return(val)
                return my_format

            self.ax.clear()
            if(self.Remaining > 0):
             self.ax.pie(self.allocation + self.unallocatedVal ,labels=self.portfolio_coins+self.unallocated,autopct = autopct_format(self.allocation+self.unallocatedVal))
            else:
             self.ax.pie(self.allocation ,labels=self.portfolio_coins,autopct = autopct_format(self.allocation))
            #draw circle
            draw_Circle(self)
            
            self.fig.canvas.draw_idle()

        def sumAllocations(name,val):
            self.TotalAllocated = 0
            self.Remaining = 100
            for value in sliderValues:
               self.TotalAllocated = self.TotalAllocated + float(value.get())
               self.Remaining = 100 - self.TotalAllocated
               if self.TotalAllocated > 100:
                            TempTotal = 0
                            x = 0
                            for x in range(0,len(sliderId)):
                                if x != name:
                                    TempTotal = TempTotal + sliderId[x].get()
                                    
                            sliderId[name].set(100 - TempTotal)
                            self.TotalAllocated = 100
                            self.Totals_String.set('{0}% of portfolio allocated, {1}% remaining to be allocated'.format(str(100),str(0)))
            
               else:
                      self.Totals_String.set('{0}% of portfolio allocated, {1}% remaining to be allocated'.format(str(self.TotalAllocated),str(self.Remaining)))
                      self.unallocatedVal.clear()
                      self.unallocatedVal.append(self.Remaining)
            
            if self.TotalAllocated <= 100:
                self.allocation[name]=val
                update(float(val))
            if self.TotalAllocated == 100:
                #self.allocation[self.portfolio_coins.index('Unallocated')]=0
                self.unallocatedVal.clear()
                self.unallocatedVal.append(self.Remaining)
                self.allocation[name]=sliderId[name].get()
                update(float(val))
           

        def AddCoin(coin):
            #add the new coin for the chart
            self.portfolio_coins.append(coin)
            self.allocation.append(0)
            widgets = list()
            row = len(self.portfolio_coins)
            sliderValues.append(StringVar())
            RowId    = tk.Label(Allocation_Frame, text=row,   relief=tk.RIDGE,  width=5)
            CoinId   = tk.Label(Allocation_Frame, text=coin,  relief=tk.RIDGE,  width=15)
            FixedId  = tk.Entry(Allocation_Frame, bg='white', relief=tk.SUNKEN, width=7, textvariable=Default_Value)
            EntryId  = tk.Entry(Allocation_Frame, bg='white', relief=tk.SUNKEN, width=7, textvariable=sliderValues[-1], state='disabled',)
            sliderid = tk.Scale(Allocation_Frame, variable=sliderValues[-1], showvalue=0, length=150, relief=tk.RIDGE, resolution=0.5, from_=0, to=100, orient='horizontal')
            sliderid.set(allocation[row-1])
            #update the command argument after the scale sliders default value has been set.
            sliderid.config(command=lambda value, name=row-1: sumAllocations(name, value))
            sliderId.append(sliderid)
            deleteBtn = tk.Button(Allocation_Frame,height=0,command=lambda coin=coin: removeCoinB(coin), width=13, text='Remove {0}'.format(coin), fg="red")
            
            RowId.grid(row=row+1,column=0, padx=paddingX)
            CoinId.grid(row=row+1,column=1, padx=paddingX)
            FixedId.grid(row=row+1,column=2, padx=paddingX)
            EntryId.grid(row=row+1,column=3, padx=paddingX)
            sliderid.grid(row=row+1,column=4, padx=paddingX)
            deleteBtn.grid(row=row+1,column=5, sticky=tk.E + tk.W, padx=paddingX, pady=3)

            widgets.append(RowId)
            widgets.append(CoinId)
            widgets.append(FixedId)
            widgets.append(EntryId)
            widgets.append(sliderid)
            widgets.append(deleteBtn)
            self.WidgetList.append(widgets)
            
        
    def print_price(self, msg):
        pair = msg['s']
        avg_price = float(msg['w'])
        time = float(msg['E'])
        mid_price = (float(msg['b']) + float(msg['a']))/2.0
        self.records[pair].write('{0},{1},{2}\n'.format(time,avg_price,mid_price))
        
    def update_actions(self):
        '''
        Calcuate required trades and update the main GUI
        '''
        
        for row in self.coins.itertuples():
        
            #tradecoin_step = np.squeeze(self.coins[self.coins['coin'] == self.trade_coin]['stepsize'].values)
            #print(tradecoin_step)
            #trade_coin_locked = self.trade_coin_Locked
            tradecoin_balance = self.trade_coin_Balance
            tradecoin_free = self.trade_coin_Free
            tradecoin_free = tradecoin_balance
            #print(tradecoin_free)
            
            dif = (row.allocation - row.actual) / 100.0 * self.total / row.price
            
            #determine the pair
            #determine the base currency
            #if base currency is bitcion....

            if dif < 0:
                side = SIDE_SELL
            if dif > 0:
                side = SIDE_BUY
            
            status = ''
            coin = row.coin
            #pair = coin + self.trade_coin
            balance = float(row.exchange_balance) - float(row.locked_balance)
            #actual = row.actual
            qty = np.absolute(dif)

            action = '{0} {1}'.format(side, round_decimal(qty, row.stepsize))
            if side == SIDE_SELL:
                price = row.bidprice
            if side == SIDE_BUY:
                price = row.askprice
            if side == SIDE_SELL and qty > balance and coin != self.trade_coin:
                status = 'Insufficient ' + coin + ' for sale'
            if coin == self.trade_coin:
                status = 'Ready'
            elif qty < row.minqty or qty * price < row.minnotional:
                status = status = 'Trade value too small ({0:.0f}%)'.format(100.0 * qty * price / row.minnotional)
            elif qty > row.maxqty:
                status = 'Trade quantity too large'
            elif side == SIDE_BUY and qty * price > float(tradecoin_free):
                status = 'Insufficient ' + self.trade_coin + ' for purchase'
            else:
                status = 'Trade Ready'
            self.portfolio.set(coin, column='Status', value=status)
            self.portfolio.set(coin, column='Action', value=action)


    def update_status(self):
        '''Update the statistics frame whenever a change occurs in balance or price'''
        value = '{0:.8f}'.format(self.total)
        diff = np.diff(self.coins['actual'].values - self.coins['allocation'].values)
        imbalance = '{0:.2f}%'.format(np.sum(np.absolute(diff)))
        self.trade_currency_value_string.set(value)
        self.imbalance_string.set(imbalance)
    
    def update_price(self,msg):
            
        
                    #print(msg['s'])
                     
                    # if coin == 'USDT' or coin == 'USDC' or coin == 'TUSD':
                    #     pair = trade_currency+coin
                    # else:
                    #     pair = coin+trade_currency
                   
                    coin = msg['s']
                    #print(coin)
                    coin = coin.replace('BTC','')
                    #print(coin)
                    ask = float(msg['a'])
                    bid = float(msg['b'])
                    askprice = round_decimal(ask,self.coins.loc[self.coins['coin'] == coin, 'ticksize'].values[0])
                    bidprice = round_decimal(bid,self.coins.loc[self.coins['coin'] == coin, 'ticksize'].values[0])
                    
                    self.portfolio.set(coin, column='Ask', value=askprice)
                    self.coins.loc[self.coins['coin'] == coin, 'askprice'] = ask
                    self.portfolio.set(coin, column='Bid', value=bidprice)
                    self.coins.loc[self.coins['coin'] == coin, 'bidprice'] = bid
                    value = (self.coins.loc[self.coins['coin'] == coin, 'exchange_balance'].values[0] +
                            self.coins.loc[self.coins['coin'] == coin, 'fixed_balance'].values[0]) * ask
                    #print(coin + "Exchange Balance: " + str(value) + " " + str(bidprice) + " " + str(askprice) + " " )
                    self.coins.loc[self.coins['coin'] == coin, 'value'] = value
                    self.total = np.sum(self.coins['value'])
                    self.coins['actual'] = self.coins.apply(lambda row: 100.0 * row.value / self.total, axis=1)
                    for row in self.coins.itertuples():
                        coin = row.coin
                        actual = '{0:.2f}%'.format(self.coins.loc[self.coins['coin'] == coin, 'actual'].values[0])
                        self.portfolio.set(coin, column='Actual', value=actual)


    def execute_transactions(self, side, dryrun):
        '''
        Calculate the required trade for each coin and execute
        them if they belong to the appropriate side
        '''

        global processIncomingFlag
        for row in self.coins.itertuples():
            #self.process_queue(flush=True)
            processIncomingFlag = True
            #ThreadedClient
            tradecoin_balance = np.squeeze(self.coins[self.coins['coin'] == self.trade_coin]['exchange_balance'].values)
            tradecoin_locked = np.squeeze(self.coins[self.coins['coin'] == self.trade_coin]['locked_balance'].values)
            tradecoin_free = tradecoin_balance - tradecoin_locked
            #print(str(tradecoin_free))
            dif = (row.allocation - row.actual) / 100.0 * self.total / row.price
            if dif < 0 and side == SIDE_BUY:
                continue
            if dif > 0 and side == SIDE_SELL:
                continue
            status = ''
            coin = row.coin
            pair = coin + self.trade_coin
            balance = float(row.exchange_balance) - float(row.locked_balance)
            actual = row.actual
            qty = np.absolute(dif)
            action = '{0} {1}'.format(side, round_decimal(qty, row.stepsize))
            last_placement = np.squeeze(self.coins[self.coins['coin'] == coin]['last_placement'].values)
            last_execution = np.squeeze(self.coins[self.coins['coin'] == coin]['last_execution'].values)            
            if side == SIDE_SELL:
                price = row.bidprice
            if side == SIDE_BUY:
                price = row.askprice
            if side == SIDE_SELL and qty > balance and coin != self.trade_coin:
                status = 'Insufficient ' + coin + ' for sale'
            if coin == self.trade_coin:
                status = 'Ready'
            elif qty < row.minqty or qty * price < row.minnotional:
                status = 'Trade value too small ({0:.0f}%)'.format(100.0 * qty * price / row.minnotional)
            elif qty > row.maxqty:
                status = 'Trade quantity too large'
            elif side == SIDE_BUY and qty * price > tradecoin_free:
                status = 'Insufficient ' + self.trade_coin + ' for purchase'
            elif last_placement == None or last_execution >= last_placement:
                trade_currency = self.trade_coin
                try:
                    self.place_order(coin, pair, self.trade_type, qty, price, side, dryrun, row.stepsize, row.ticksize)
                except (BinanceRequestException,
                        BinanceAPIException,
                        BinanceOrderException,
                        BinanceOrderMinAmountException,
                        BinanceOrderMinPriceException,
                        BinanceOrderMinTotalException,
                        BinanceOrderUnknownSymbolException,
                        BinanceOrderInactiveSymbolException) as e:
                    self.portfolio.set(coin, column='Event', value=e.message)
                else:
                    status = 'Trade Ready'
                    if not dryrun:
                        self.trades_placed += 1
                        status = 'Trade Placed'
                        self.portfolio.set(coin, column='Event', value='Trade Placed')
            self.portfolio.set(coin, column='Status', value=status)
            self.portfolio.set(coin, column='Action', value=action)
            
            
    def automation(self, toggle=False):
        if toggle:
            if not self.automate.get():
                self.automate_text.set('Stop Automation')
            else:
                self.automate_text.set('Start Automation')
            self.automate.set(not self.automate.get())
        if self.automate.get():
            self.execute_sells()
            self.execute_buys()
            self.rebalance_callback = self.parent.after(self.rebalance_time, self.automation)
        else:
            self.parent.after_cancel(self.rebalance_callback)
    
    def execute_sells(self):
        '''
        Perform any sells required by overachieving coins
        '''
        self.execute_transactions(side=SIDE_SELL, dryrun=False)

    def execute_buys(self):
        '''
        Perform any buys required by underachieving coins
        '''
        self.execute_transactions(side=SIDE_BUY, dryrun=False)

    def dryrun(self):
        '''
        perform a dry run to list what trades are required
        '''
        self.execute_transactions(side=SIDE_SELL, dryrun=True)
        self.execute_transactions(side=SIDE_BUY, dryrun=True)        
        
    def place_order(self, coin, pair, trade_type,
                    quantity, price, side, dryrun,
                    stepsize, ticksize):
        '''
        Format and place an order using the Binance API
        '''
        if trade_type == 'LIMIT':
            if dryrun:
                order = self.client.create_test_order(symbol=pair,
                                                      side=side,
                                                      type=ORDER_TYPE_LIMIT,
                                                      timeInForce=TIME_IN_FORCE_GTC,
                                                      quantity=round_decimal(quantity, stepsize),
                                                      price=round_decimal(price, ticksize))
            else:
                order = self.client.create_order(symbol=pair,
                                                 side=side,
                                                 type=ORDER_TYPE_LIMIT,
                                                 timeInForce=TIME_IN_FORCE_GTC,
                                                 quantity=round_decimal(quantity, stepsize),
                                                 price=round_decimal(price, ticksize))
        elif trade_type == 'MARKET':
            if dryrun:
                order = self.client.create_test_order(symbol=pair,
                                                      side=side,
                                                      type=ORDER_TYPE_MARKET,
                                                      quantity=round_decimal(quantity, stepsize))
            else:
                order = self.client.create_order(symbol=pair,
                                                 side=side,
                                                 type=ORDER_TYPE_MARKET,
                                                 quantity=round_decimal(quantity, stepsize))
        if not dryrun:
            self.coins.loc[self.coins['coin'] == coin, 'last_placement'] = time.mktime(datetime.now().timetuple())
            
    def column_headers(self):
        ''' define human readable aliases for the headers in trade execution reports. '''
        return {'e': 'event_type',
                'E': 'event_time',
                's': 'symbol',
                'c': 'client_order_id',
                'S': 'side',
                'o': 'type',
                'O': 'order_creation_time',
                'f': 'time_in_force',
                'q': 'order_quantity',
                'p': 'order_price',
                'P': 'stop_price',
                'F': 'iceberg_quantity',
                'g': 'ignore_1',
                'C': 'original_client_order_id',
                'x': 'current_execution_type',
                'X': 'current_order_status',
                'r': 'order_reject_reason',
                'i': 'order_id',
                'l': 'last_executed_quantity',
                'z': 'cumulative_filled_quantity',
                'Z': 'cumulative_quote_asset_transacted_qty',
                'L': 'last_executed_price',
                'n': 'commission_amount',
                'N': 'commission_asset',
                'T': 'transaction_time',
                't': 'trade_id',
                'I': 'ignore_2',
                'w': 'order_working',
                'm': 'maker_side',
                'M': 'ignore_3',
                'Y': 'last_quote_asset_transacted_qty'}
      
class ThreadedClient:
    """
    Launch the main part of the GUI and the worker thread. periodicCall and
    endApplication could reside in the GUI part, but putting them here
    means that you have all the thread controls in a single place.
    """
    def __init__(self, master,queue):
        
        self.lastQsize = 0
        self.queueLength = 0
        """
        Start the GUI and the asynchronous threads. We are in the main
        (original) thread of the application, which will later be used by
        the GUI as well. We spawn a new thread for the worker (I/O).
        """
        self.master = master
        self.queue = queue

        # Set up the GUI part
        self.gui = GuiPart(master, queue)

        self.processIncoming(flush=False)
    

    def get_msg(self):
            
                 msg = self.queue.get()
                 
                 if msg['e'] == '24hrTicker':
                    self.gui.update_price(msg)
                    self.gui.update_actions()
                    self.gui.update_status()
                 elif msg['e'] == 'outboundAccountInfo':
                    self.gui.update_balance(msg)
                
                 global processed
                 processed = processed + 1
                 return           
                
    def processIncoming(self,flush=False):
                global received
                global maxThreads 
                global processIncomingFlag
                '''
                Check for new messages in the queue periodically.
                Recursively calls itself to perpetuate the process.
                '''
                self.lastQsize = self.queueLength
                self.queueLength = self.queue.qsize()
                threadcount = threading.active_count()
                if self.queueLength > 0:
                        received = received + 1
                        self.gui.messages_string.set('Threads {0}, Queued {1}, Rec {2}, Proc {3}'.format(str(threadcount),self.queueLength, received, processed))  
                        self.get_msg()

                        maxThreads= maxThreads + 1

                        if(threadcount < 13 and threadcount < maxThreads and self.queueLength >= self.lastQsize):
                          self.thread2 = threading.Thread(target=self.processIncoming)
                          self.thread2.start()
                          #Thread completed assigned jobs, retasking....
                          self.master.after_idle(self.master.after,1,self.processIncoming)
                else:
                        
                        self.gui.messages_string.set('Threads {0}, Queued {1}, Rec {2}, Proc {3}'.format(str(threadcount),self.queueLength, received, processed))  
                        if threadcount > maxThreads:
                           maxThreads = maxThreads - 1
                           return
                        
                        if maxThreads <= 3:
                           maxThreads = 3

                self.master.after_idle(self.master.after,250,self.processIncoming)
   
# Data Generator which will generate Data
def GetSocketData(client,queue,trade_currency,coins):
   
    def process_message(msg):
            queue.put(msg)

    def process_m_message(msg):
            queue.put(msg['data'])
    
    Stream_List = []
    symbols = coins['coin'].tolist()
    Stream_List = [str.lower(x) + str.lower(trade_currency) + '@ticker' for x in symbols]
    
    bm = BinanceSocketManager(client)
    bm.start_multiplex_socket(Stream_List, process_m_message)
    
    bm.start_user_socket(process_message)
    bm.start()
    
if __name__ == '__main__':
   
   rand = random.Random(  )
   root = tk.Tk()
   client = ThreadedClient(root,queue)
   root.mainloop()
   t1.join()
