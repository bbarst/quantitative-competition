import pandas as pd

def data_process(responses_list):
    
    instrumentsID = [item.get("instrument") for item in responses_list[0]]
    times = [item[0].get("lob").get("localtime") for item in responses_list]
    temp = pd.DataFrame(index=instrumentsID, columns=times)
    data = {}

    # generating limit_up_price, limit_down_price, last_price, trade_volume, trade_value
    keys = ['limit_up_price', 'limit_down_price', 'last_price', 'trade_volume', 'trade_value']
    for key in keys:
        df = temp.copy()
        for i in range(len(times)):
            for j in range(len(instrumentsID)):
                df.iloc[j,i] = responses_list[i][j]["lob"][key]
        data[key] = df.copy()
    
    # generating askprice, askvolume, bidprice, bidvolume
    for k in range(10):
        df1,df2,df3,df4 = temp.copy(), temp.copy(), temp.copy(), temp.copy()
        for i in range(len(times)):
            for j in range(len(instrumentsID)):
                df1.iloc[j,i] = responses_list[i][j]["lob"]["askprice"][k]
                df2.iloc[j,i] = responses_list[i][j]["lob"]["askvolume"][k]
                df3.iloc[j,i] = responses_list[i][j]["lob"]["bidprice"][k]
                df4.iloc[j,i] = responses_list[i][j]["lob"]["bidvolume"][k]
        data[f"askprice{k+1}"] = df1.copy()
        data[f"askvolume{k+1}"] = df2.copy()
        data[f"bidprice{k+1}"] = df3.copy()
        data[f"bidvolume{k+1}"] = df4.copy()
    
    return data