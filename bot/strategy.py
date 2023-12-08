import numpy as np
from scipy.linalg import expm
from aux import logger, ConvertToSimTime_us, InterfaceClass


class QuantBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.api = InterfaceClass("https://trading.competition.ubiquant.com")
        #  the activeorder_buy/sell is of the form [[order_index1,order_price1,order_volume1],
        #  [order_index2,order_price2,order_volume2]...]
        self.activeorder_buy = [np.empty((0, 3)) for i in range(29)]
        self.activeorder_sell = [np.empty((0, 3)) for i in range(29)]  # update active order
        self.position = np.zeros(29)
        self.real_pos = np.zeros(29)
        self.buy_price = np.zeros(29)
        self.sell_price = np.zeros(29)
        self.trade_list = [[] for i in range(29)]

        self.volume_list = [100 for i in range(29)]
        self.midprice = 0
        self.kappa_list = []
        self.lambda_list = []
        self.penalty_list = []
        self.alpha_list = []
        self.T = 14400
        self.upper_q = [1 for i in range(29)]

    def login(self):
        response = self.api.sendLogin(self.username, self.password)
        if response["status"] == "Success":
            self.token_ub = response["token_ub"]
            logger.info("Login Success: {}".format(self.token_ub))
        else:
            logger.info("Login Error: ", response["status"])

    def GetInstruments(self):
        response = self.api.sendGetInstrumentInfo(self.token_ub)
        if response["status"] == "Success":
            self.instruments = []
            for instrument in response["instruments"]:
                self.instruments.append(instrument["instrument_name"])
            logger.info("Get Instruments: {}".format(self.instruments))

    def init(self, kappa_list, penalty_list, lambda_list, upper_q_list, alpha_list):
        response = self.api.sendGetGameInfo(self.token_ub)
        if response["status"] == "Success":
            self.start_time = response["next_game_start_time"]
            self.running_days = response["next_game_running_days"]
            self.running_time = response["next_game_running_time"]
            self.time_ratio = response["next_game_time_ratio"]
        self.GetInstruments()
        self.day = 0

        self.activeorder_buy = [np.empty((0, 3)) for i in range(
            29)]  # the activeorder_buy/sell is of the form [[order_index1,order_price1,order_volume1],[order_index2,order_price2,order_volume2]...]
        self.activeorder_sell = [np.empty((0, 3)) for i in range(29)]  # update active order
        self.position = np.zeros(29)
        self.real_pos = np.zeros(29)
        self.trade_list = [[] for i in range(29)]
        self.kappa_list = kappa_list
        self.lambda_list = lambda_list
        self.penalty_list = penalty_list
        self.upper_q = upper_q_list
        self.alpha_list = alpha_list

    def bod(self):
        pass

    def work(self, target):
        kappa_pos = self.kappa_list[target][0]
        kappa_neg = self.kappa_list[target][1]
        kappa = (kappa_pos + kappa_neg) / 2
        lambda_pos = self.lambda_list[target][0]
        lambda_neg = self.lambda_list[target][1]
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[target])  # get LOB
        trade_info = self.api.sendGetTrade(self.token_ub, self.instruments[
            target])  # trade_info contains all order being traded in the last 0.1s, get trade_info so you can update your activeorder, refer to picture in wechat group for the form of trade_info
        t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)

        # update active order
        if (trade_info['trade_list']):
            if (trade_info['trade_list'][-1]['trade_index']) not in self.trade_list[target]:
                for order in trade_info['trade_list']:
                    if order['trade_index'] not in self.trade_list[target]:  # 这里可以优化
                        self.trade_list.append(order['trade_index'])
                        if order['order_index'] in self.activeorder_buy[target][:,
                                                   0]:  # for every buy order seccessfully traded, add volume to position and update your activeorder
                            self.position[target] += order['trade_volume']
                            index = np.where(self.activeorder_buy[target][:, 0] == order['order_index'])
                            if order['remain_volume'] == 0:
                                self.activeorder_buy[target] = np.delete(self.activeorder_buy[target], index, axis=0)
                            else:
                                self.activeorder_buy[target][index, 2] = order['remain_volume']
                        elif order['order_index'] in self.activeorder_sell[target][:, 0]:  # same as buy
                            self.new_sell = True
                            self.position[target] -= order['trade_volume']
                            index = np.where(self.activeorder_sell[target][:, 0] == order['order_index'])
                            if order['remain_volume'] == 0:
                                self.activeorder_sell[target] = np.delete(self.activeorder_sell[target], index, axis=0)
                            else:
                                self.activeorder_sell[target][index, 2] = order['remain_volume']
            self.activeorder_buy[target] = self.activeorder_buy[target][self.activeorder_buy[target][:, 1].argsort()]
            self.activeorder_sell[target] = self.activeorder_sell[target][
                self.activeorder_sell[target][:, 1].argsort()]  # sort by price, row 0 is minimum
            self.real_pos[target] = self.position[target] - self.activeorder_sell[target][:, 2].sum()
        # strategy part
        if LOB["status"] == "Success":

            # get LOB information
            askprice = np.array([float(k) for k in LOB["lob"]["askprice"]])
            bidprice = np.array([float(k) for k in LOB["lob"]["bidprice"]])
            askvol = np.array([float(k) for k in LOB["lob"]["askvolume"]])
            bidvol = np.array([float(k) for k in LOB["lob"]["bidvolume"]])
            mid = (askprice[0] + bidprice[0]) / 2

            # calculate dalta
            matrix_size = self.upper_q[target] + 1
            matrix = np.eye(matrix_size) * np.arange(0, matrix_size) ** 2 * (-self.penalty_list[target]) * kappa

            matrix[np.arange(1, matrix_size), np.arange(matrix_size - 1)] = [lambda_pos / np.e for i in
                                                                             range(matrix_size - 1)]
            matrix[np.arange(matrix_size - 1), np.arange(1, matrix_size)] = [lambda_neg / np.e for i in
                                                                             range(matrix_size - 1)]
            matrix = matrix * (self.T - t) * 30 / 14400

            omega = expm(matrix) @ np.exp(np.arange(0, matrix_size) ** 2 * (-self.alpha_list[target]) * kappa)
            h = 1 / kappa * np.log(omega)
            q = int(self.position[target] / 100)
            if q != 0:
                delta_pos = 1 / kappa_pos - h[q - 1] + h[q]
            else:
                delta_pos = float('inf')
            if q != self.upper_q[target]:
                delta_neg = 1 / kappa_neg - h[q + 1] + h[q]
            else:
                delta_neg = float('inf')

            # send/cancel order
            buy_price = np.floor((mid - delta_neg) * 100) / 100
            sell_price = np.ceil((mid + delta_pos) * 100) / 100
            sell_traded = False
            buy_traded = False
            if (sell_price != self.sell_price[target]) and (delta_pos < 100):
                if self.activeorder_sell[target].size:
                    res = self.api.sendCancel(self.token_ub, self.instruments[target], t,
                                              int(self.activeorder_sell[target][0, 0]))

                    if res['status'] != 'Success':
                        sell_traded = True
                    else:
                        self.activeorder_sell[target] = self.activeorder_sell[target][1:]
                if not sell_traded:
                    response = self.api.sendOrder(self.token_ub, self.instruments[target], t, 'sell', sell_price,
                                                  self.volume_list[target])
                    self.activeorder_sell[target] = np.append(
                        self.activeorder_sell[target],
                        [[response['index'], sell_price, self.volume_list[target]]],
                        axis=0)
                    self.sell_price[target] = sell_price
            if (buy_price != self.buy_price[target]) and (delta_neg < 100):
                if self.activeorder_buy[target].size:
                    res = self.api.sendCancel(self.token_ub, self.instruments[target], t,
                                              int(self.activeorder_buy[target][0, 0]))

                    if res['status'] != 'Success':
                        buy_traded = True
                    else:
                        self.activeorder_buy[target] = self.activeorder_buy[target][1:]
                if not buy_traded:
                    response = self.api.sendOrder(self.token_ub, self.instruments[target], t, 'buy', buy_price,
                                                  self.volume_list[target])
                    self.activeorder_buy[target] = np.append(self.activeorder_buy[target],
                                                             [[response['index'], buy_price, self.volume_list[target]]],
                                                             axis=0)
                    self.buy_price[target] = buy_price

    def cancel_all_order(self, target):
        asset = self.instruments[target]

        t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)
        # update activeorder
        response = self.api.sendGetActiveOrder(self.token_ub)

        name = response['instruments'][target]['instrument_name']
        for order in response['instruments'][target]['active_orders']:
            self.api.sendCancel(self.token_ub, name, t, order['order_index'])
        response = self.api.sendGetUserInfo(self.token_ub)
        volume = response['rows'][target]['share_holding']
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, asset)
        if LOB["status"] == "Success":
            askprice = np.array([float(i) for i in LOB["lob"]["askprice"]])
            bidprice = np.array([float(i) for i in LOB["lob"]["bidprice"]])
            self.api.sendOrder(self.token_ub, asset, t, "sell", bidprice[0] - 0.02, volume)

    def close_position(self, asset, t, askprice, bidprice):
        for order in self.activeorder_sell:
            self.api.sendCancel(self.token_ub, asset, t, int(order[0]))

        for order in self.activeorder_buy:
            self.api.sendCancel(self.token_ub, asset, t, int(order[0]))
        res = self.api.sendGetUserInfo(self.token_ub)
        self.position = res['rows'][2]['share_holding']
        self.activeorder_sell = np.empty((0, 4))
        self.activeorder_buy = np.empty((0, 3))
        if self.position:
            response = self.api.sendOrder(self.token_ub, asset, t, "sell", bidprice, self.position)
            self.activeorder_sell = np.array([[response['index'], bidprice, self.position, 0.02]])

        self.real_pos = 0

    def eod(self):
        pass

    def final(self):
        pass