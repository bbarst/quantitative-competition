from aux import ConvertToSimTime_us
from strategy import QuantBot
from concurrent.futures import ProcessPoolExecutor

SimTimeLen = 14400
endWaitTime = 300


def bot_fun(symbol):
    kappa_list = [[100, 100] for i in range(29)]
    penalty_list = [0.0002 for i in range(29)]
    lambda_list = [[1, 1] for i in range(29)]
    upper_q_list = [3 for i in range(29)]
    alpha_list = [0.0001 for i in range(29)]
    last_t = 0

    # run the strategy
    bot = QuantBot('UBIQ_TEAM359', "eeKvoJiLv")
    bot.login()
    bot.init(kappa_list, penalty_list, lambda_list, upper_q_list, alpha_list)

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
                if int(t) % 100:
                    if len(bot.trade_list[symbol]) > 10:
                        bot.trade_list[symbol] = bot.trade_list[symbol][-10:]
        bot.eod()
        bot.day += 1
    bot.final()


if __name__ == '__main__':
    workers = 1
    symbol_list = [18]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        executor.map(bot_fun, symbol_list)
