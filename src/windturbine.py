import numpy as np
import pandas as pd
import os

class Windturbine():
    def __init__(self, wt_number='5'):
        self.turbine_properties = pd.read_csv('config' + os.sep + 'turbines' + os.sep + str(wt_number) +'.csv', index_col=0)
        self.power_curve = self.turbine_properties.power.values
        self.wind_curve = self.turbine_properties.wind.values

    def get_max_power(self):
        max_power = self.power_curve.max()
        return max_power