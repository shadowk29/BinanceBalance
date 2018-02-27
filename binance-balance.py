import Tkinter as tk
import ttk
import tkFileDialog
import pandas as pd


class BalanceGUI(tk.Frame):
    def __init__(self, parent, coins):
        tk.Frame.__init__(self, parent)
        
        parent.deiconify()
        self.coins = coins        

        #portfolio display
        self.portfolio_view = tk.LabelFrame(parent, text='Portfolio')
        self.portfolio_view.grid(row=0,column=0, sticky=tk.E+tk.W)
        self.portfolio = ttk.Treeview(self.portfolio_view)
        self.portfolio['columns']=('Stored','Exchange', 'Target','Actual', 'Action')
        for label in self.portfolio['columns']:
            if label != 'Action':
                self.portfolio.column(label, width=100)
            else:
                self.portfolio.column(label, width=300)
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

        
        self.refresh_button = tk.Button(self.controls_view, text='Refresh', command=self.refresh, state='disabled')
        self.refresh_button.grid(row=1,column=2, sticky=tk.E+tk.W)
        self.dryrun_button = tk.Button(self.controls_view, text='Dry Run', command=self.dryrun, state='disabled')
        self.dryrun_button.grid(row=1,column=3, sticky=tk.E+tk.W)
        self.rebalance_button = tk.Button(self.controls_view, text='Rebalance', command=self.rebalance, state='disabled')
        self.rebalance_button.grid(row=1,column=4, sticky=tk.E+tk.W)

        self.ordertype = tk.StringVar()
        self.ordertype.set('Order Type')
        self.orderopt = tk.OptionMenu(self.controls_view, self.ordertype, 'Market', 'Adaptive Limit', 'Median Limit')
        self.orderopt.grid(row=1, column=0, stick=tk.E+tk.W)
        self.orderopt['state'] = 'disabled'

        self.trade_currency = tk.StringVar()
        self.trade_currency.set('Trade Currency')
        self.trade_currency_opt = tk.OptionMenu(self.controls_view, self.trade_currency, 'BTC', 'ETH', 'USDT', 'Automatic')
        self.trade_currency_opt.grid(row=1, column=1, stick=tk.E+tk.W)
        self.trade_currency_opt['state'] = 'disabled'
        

        #streaming display
        self.stream_view = tk.LabelFrame(parent, text='Current State')
        self.stream_view.grid(row=2, column=0, sticky=tk.E+tk.W)
        self.commands = tk.StringVar()
        self.stream = tk.Label(self.stream_view, textvariable = self.commands)
        self.stream.grid(row=0, column=0, sticky=tk.E+tk.W)

    def api_enter(self):
        self.api_key = self.key_entry.get()
        self.key_entry.delete(0,'end')
        self.api_secret = self.secret_entry.get()
        self.secret_entry.delete(0,'end')

        
        self.key_entry['state'] = 'disabled'
        self.secret_entry['state'] = 'disabled'
        self.login['state'] = 'disabled'
        self.refresh_button['state'] = 'normal'
        self.dryrun_button['state'] = 'normal'
        self.orderopt['state'] = 'normal'
        self.trade_currency_opt['state'] = 'normal'
        self.populate_portfolio()

    def dryrun(self):
        self.rebalance_button['state'] = 'normal'
        

    def populate_portfolio(self):
        i = 0
        for row in self.coins.itertuples():
            self.portfolio.insert("" , i, text=row.coin, values=(row.fixed, 0, '{0} %'.format(row.allocation), 0, 'None'))
            i += 1
        
    def refresh(self):
        pass

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
