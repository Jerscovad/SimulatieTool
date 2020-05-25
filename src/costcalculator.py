"""calculate the cost of panels, windmills and storage"""

import numpy as np
import pandas as pd
from copy import copy
from simulator import Simulator
from location import Location
from windturbine import Windturbine

class CostCalculator():
    """
        class to calculate the cost of a configuration
        sp_cost_per_sm = Solar panel cost per Square Meter
        st_cost_per_kwh = Storage Cost per KWH
        
    """

    def __init__(self, sp_cost_per_sm, st_cost_per_kwh, target_kw, shortage_cost, wt_cost_per_kw, 
                 surplus_cost_per_kw, train_by_price=True, windturbine=None):
        self.sp_cost_per_sm = sp_cost_per_sm
        self.st_cost_per_kwh = st_cost_per_kwh
        self.target_kw = target_kw
        self.shortage_cost = shortage_cost
        self.wt_cost_per_kw = wt_cost_per_kw
        self.surplus_cost_per_kw = surplus_cost_per_kw
        self.train_by_price = train_by_price
        self.windturbine = windturbine
        self.turbine_power = windturbine.get_max_power()

    def calculate_cost(self, kwh_array, sp_sm, turbines):

        surplus_array = kwh_array - self.target_kw
        cumulative_array = np.cumsum(surplus_array)
        storage = 0
        total_surplus = max(0,cumulative_array[-1])
        shortage = min(0, cumulative_array[-1]) * -1
        if shortage == 0:
            smaller_than_zero = np.where(cumulative_array < 0)[0]
            if smaller_than_zero.shape[0] > 0:
                new_start = smaller_than_zero[-1] + 1
                surplus_array = np.concatenate((surplus_array[new_start:], surplus_array[:new_start]), axis=0)
                cumulative_array = np.cumsum(surplus_array)
            declining = surplus_array < 0
            while np.any(declining) and storage < np.max(cumulative_array):
                lowest = np.min(cumulative_array[declining])
                cumulative_array -= lowest
                new_start = np.where(np.logical_and(np.equal(cumulative_array, 0), declining))[0][-1] + 1
                storage = max(storage, np.max(cumulative_array[:new_start]))
                cumulative_array = cumulative_array[new_start:]
                declining = declining[new_start:]

        # windturbine calculation
        # Max power * number of turbines * cost per kw
        wm_cost = self.turbine_power * turbines * self.wt_cost_per_kw

        # Check which cost is requested.
        if self.train_by_price:
            cost = sp_sm * self.sp_cost_per_sm + \
                   wm_cost + \
                   storage * self.st_cost_per_kwh + \
                   shortage * self.shortage_cost 
        else:
            cost = shortage * self.shortage_cost + \
                   total_surplus * self.surplus_cost_per_kw + \
                   storage * self.st_cost_per_kwh

        return cost
        
    def get_stats(self, kwh_array, sp_sm, turbines):
        surplus_array = kwh_array - self.target_kw
        cumulative_array = np.cumsum(surplus_array)
        total_surplus = max(0,cumulative_array[-1])        
        storage = 0
        shortage = min(0, cumulative_array[-1]) * -1
        if shortage == 0:
            smaller_than_zero = np.where(cumulative_array < 0)[0]
            if smaller_than_zero.shape[0] > 0:
                new_start = smaller_than_zero[-1] + 1
                surplus_array = np.concatenate((surplus_array[new_start:], surplus_array[:new_start]), axis=0)
                cumulative_array = np.cumsum(surplus_array)
            declining = surplus_array < 0
            while np.any(declining) and storage < np.max(cumulative_array):
                lowest = np.min(cumulative_array[declining])
                cumulative_array -= lowest
                new_start = np.where(np.logical_and(np.equal(cumulative_array, 0), declining))[0][-1] + 1
                storage = max(storage, np.max(cumulative_array[:new_start]))
                cumulative_array = cumulative_array[new_start:]
                declining = declining[new_start:]

        wm_cost = self.turbine_power * turbines * self.wt_cost_per_kw

        # calculate the final cost
        solar_cost = sp_sm * self.sp_cost_per_sm
        wind_cost = wm_cost
        storage_cost = storage * self.st_cost_per_kwh
        shortage_cost = shortage * self.shortage_cost

        cost = solar_cost + \
        wind_cost + \
        storage_cost + \
        shortage_cost
        stat_dict = {
            'cost': cost,
            'solar_cost': solar_cost,
            'wind_cost': wind_cost,
            'storage_cost': storage_cost,
            'shortage_cost': shortage_cost,
            'total_surplus': total_surplus,
            'total_shortage': shortage,
            'total_storage': storage,
        }
        return stat_dict


if __name__ == '__main__':

    simulator = Simulator(Location('volkel'),'2018', Windturbine(5))
    calculator = Costcalculator(160, 400, 6000, 1000000, 1070)