from aux import ConvertToSimTime_us
from strategy import QuantBot
from concurrent.futures import ProcessPoolExecutor
import numpy as np

SimTimeLen = 14400
endWaitTime = 300

# global gt_u, gt_a
# global pnl, sharp, orders, error_orders, order_value, trade_value, commision, total_position, remain_funds
# global user_instruments, active_instruments


def bot_fun(symbol):
    kappa_list = [[100, 100] for i in range(29)]
    penalty_list = [0.0002 for i in range(29)]
    lambda_list = [[1, 1] for i in range(29)]
    upper_q_list = [3 for i in range(29)]
    alpha_list = [0.0001 for i in range(29)]
    last_t = 0
    last_t1 = 0
    last_t2 = 0

    # run the strategy
    bot = QuantBot('UBIQ_TEAM359', "eeKvoJiLv")
    bot.login()
    bot.init(kappa_list, penalty_list, lambda_list, upper_q_list, alpha_list)
    SimTimeLen = 14400
    endWaitTime = 300
    while True:
        if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) < SimTimeLen:
            break
        else:
            bot.day += 1

    while bot.day <= bot.running_days:
        while True:
            if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) > -900:
                break
        bot.bod()
        now = round(ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time))
        for s in range(now, SimTimeLen + endWaitTime):
            while True:
                if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) >= s:
                    break
            t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
            # logger.info("Work Time: {}".format(t))
            if (t < SimTimeLen - 30) and (t - last_t) > 0.7:
                bot.work(symbol)
                last_t = t
                if (t - last_t1) > 100:
                    if len(bot.trade_list[symbol]) > 10:
                        bot.trade_list[symbol] = bot.trade_list[symbol][-10:]
                    last_t1 = t
                if (t - last_t2) > 200:
                    last_t2 = t
                    bot.activeorder_buy[symbol] = np.empty((0, 3))
                    bot.activeorder_sell[symbol] = np.empty((0, 3))
                    response = bot.api.sendGetActiveOrder(bot.token_ub)
                    if response['status'] == 'Success':
                        for order in response['instruments'][symbol]['active_orders']:
                            if order['direction'] == 'buy':
                                bot.activeorder_buy[symbol] = np.append(bot.activeorder_buy[symbol], [
                                    [order['order_index'], order['order_price'], order['volume']]], axis=0)
                            else:
                                bot.activeorder_sell[symbol] = np.append(bot.activeorder_sell[symbol], [
                                    [order['order_index'], order['order_price'], order['volume']]], axis=0)
                    response = bot.api.sendGetUserInfo(bot.token_ub)
                    if response['status'] == 'Success':
                        bot.position[symbol] = response['rows'][symbol]['share_holding']

        bot.eod()
        bot.day += 1
    bot.final()


if __name__ == '__main__':
    workers = 1
    symbol_list = [18]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        executor.map(bot_fun, symbol_list)

    # kappa_list = [[100, 100] for i in range(29)]
    # penalty_list = [0.0002 for i in range(29)]
    # lambda_list = [[1, 1] for i in range(29)]
    # upper_q_list = [3 for i in range(29)]
    # alpha_list = [0.0001 for i in range(29)]
    # last_t = 0
    # bot = QuantBot('UBIQ_TEAM359', "eeKvoJiLv")
    # bot.login()
    # bot.init(kappa_list, penalty_list, lambda_list, upper_q_list, alpha_list)
    # bot.cancel_all_order(18)
