import numpy as np
import pandas as pd
from stockstats import StockDataFrame as Sdf
from finrl.config import config


class FeatureEngineer:
    """Provides methods for retrieving daily stock data from
    Yahoo Finance API

    Attributes
    ----------
        df
        feature_number : str
            start date of the data (modified from config.py)
        use_technical_indicator : str
            end date of the data (modified from config.py)
        use_turbulence : list
            a list of stock tickers (modified from config.py)

    Methods
    -------
    fetch_data()
        Fetches data from yahoo API

    """
    def __init__(self, 
        df,
        feature_number = 5,
        use_technical_indicator=True,
        use_turbulence=False):

        self.df = df
        self.feature_number = feature_number
        type_list = self.__get_type_list(feature_number)
        self.__features = type_list
        self.__data_columns = config.DEFAULT_DATA_COLUMNS + self.__features
        self.use_technical_indicator = use_technical_indicator
        self.tech_indicator_list = config.TECHNICAL_INDICATORS_LIST
        self.use_turbulence=use_turbulence


    def preprocess_data(self):
        """main method to do the feature engineering
        @:param config: source dataframe
        @:return: a DataMatrices object
        """
        df = self.df.copy()

        # add technical indicators
        # stockstats require all 5 columns
        if (self.use_technical_indicator==True) & (self.feature_number>=5):
            # add technical indicators using stockstats
            df=self.__add_technical_indicator(df)
            print("Successfully added technical indicators")

        # add turbulence index for multiple stock
        if self.use_turbulence==True:
            df = self.__add_turbulence(df)
            print("Successfully added turbulence index")

       
        # fill the missing values at the beginning and the end
        df=df.fillna(method='bfill').fillna(method="ffill")
        return df


    def __add_technical_indicator(self, data):
            """
            calcualte technical indicators
            use stockstats package to add technical inidactors
            :param data: (df) pandas dataframe
            :return: (df) pandas dataframe
            """
            df = data.copy()
            stock = Sdf.retype(df.copy())
            unique_ticker = stock.tic.unique()

            for indicator in self.tech_indicator_list:
                indicator_df = pd.DataFrame()
                for i in range(len(unique_ticker)):
                    try:
                        temp_indicator = stock[stock.tic == unique_ticker[i]][indicator]
                        temp_indicator= pd.DataFrame(temp_indicator)
                        indicator_df = indicator_df.append(temp_indicator, ignore_index=True)
                    except Exception as e:
                        print(e)
                df[indicator] = indicator_df
            return df



    def __add_turbulence(self, data):
        """
        add turbulence index from a precalcualted dataframe
        :param data: (df) pandas dataframe
        :return: (df) pandas dataframe
        """
        df = data.copy()
        turbulence_index = self.__calcualte_turbulence(df)
        df = df.merge(turbulence_index, on='date')
        df = df.sort_values(['date','tic']).reset_index(drop=True)
        return df

    def __get_type_list(self, feature_number):
        """
        :param feature_number: an int indicates the number of features
        :return: a list of features n
        """
        if feature_number == 1:
            type_list = ["close"]
        elif feature_number == 2:
            type_list = ["close", "volume"]
            #raise NotImplementedError("the feature volume is not supported currently")
        elif feature_number == 3:
            type_list = ["close", "high", "low"]
        elif feature_number == 4:
            type_list = ["close", "high", "low", "open"]
        elif feature_number == 5:
            type_list = ["close", "high", "low", "open","volume"]  
        else:
            raise ValueError("feature number could not be %s" % feature_number)
        return type_list


    def __calcualte_turbulence(self, data):
        """calculate turbulence index based on dow 30"""
        # can add other market assets
        df = data.copy()
        df_price_pivot=df.pivot(index='date', columns='tic', values='close')
        unique_date = df.date.unique()
        # start after a year
        start = 252
        turbulence_index = [0]*start
        #turbulence_index = [0]
        count=0
        for i in range(start,len(unique_date)):
            current_price = df_price_pivot[df_price_pivot.index == unique_date[i]]
            hist_price = df_price_pivot[[n in unique_date[0:i] for n in df_price_pivot.index ]]
            cov_temp = hist_price.cov()
            current_temp=(current_price - np.mean(hist_price,axis=0))
            temp = current_temp.values.dot(np.linalg.inv(cov_temp)).dot(current_temp.values.T)
            if temp>0:
                count+=1
                if count>2:
                    turbulence_temp = temp[0][0]
                else:
                    #avoid large outlier because of the calculation just begins
                    turbulence_temp=0
            else:
                turbulence_temp=0
            turbulence_index.append(turbulence_temp)
        
        
        turbulence_index = pd.DataFrame({'date':df_price_pivot.index,
                                         'turbulence':turbulence_index})
        return turbulence_index
