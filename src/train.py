"""train a single group"""

import numpy as np
import wx
import pandas as pd
from calculate_cost import CostCalculator
from genetic_algorith import GeneticAlgorith
from multiprocessing import Process, Value
from generators import Windturbine
from simulator import Simulator
from location import Location

N_PANELS = 4
N_SOLAR_FEATURES = N_PANELS * 3

N_WIND_FEATURES = 1
N_WIND_MAX = 10
N_WIND_MIN = 0
N_FEATURES = N_SOLAR_FEATURES + N_WIND_FEATURES


def train(parent, n_generations=100, group_size=100, surface_min=0, surface_max=10000000, angle_min=0, angle_max=90, orientation_min=-180, orientation_max=180, 
          mutationPercentage=50, N_WIND_MIN=0, N_WIND_MAX=10, turbine_height=100,
          cost_calculator=None, simulator=None, windturbineType=4, sp_efficiency=16):
    """train genetic algorithm"""
    genetic_algorithm = GeneticAlgorith(mutationPercentage, 150, 6, 2, 2, True)

    # parameter 2 kosten voor accu per kWh
    if cost_calculator is None:
        cost_calculator = CostCalculator(160, 400, 6000, 1000000)

    turbine = Windturbine(windturbineType)

    if simulator is None:
        simulator = Simulator(Location('NEN'),'2018', turbine)

    solar_values = np.random.rand(group_size, N_SOLAR_FEATURES)
    solar_values[:, 0::3] *= (surface_max - surface_min)
    solar_values[:, 0::3] += surface_min
    solar_values[:, 1::3] *= (angle_max - angle_min)
    solar_values[:, 1::3] += angle_min
    solar_values[:, 2::3] *= (orientation_max - orientation_min)
    solar_values[:, 2::3] += orientation_min
    wind_values = np.random.rand(group_size, N_WIND_FEATURES)
    wind_values[0] *= N_WIND_MAX
    group_values = np.concatenate((solar_values, wind_values), axis=1)  # concatenate on features

    # prepare min and max arrays to truncate values later
    highest_allowed = np.zeros_like(group_values)
    lowest_allowed = np.zeros_like(group_values)
    highest_allowed[:, 0:N_SOLAR_FEATURES:3] = surface_max
    lowest_allowed[:, 0:N_SOLAR_FEATURES:3] = surface_min
    highest_allowed[:, 1:N_SOLAR_FEATURES:3] = angle_max
    lowest_allowed[:, 1:N_SOLAR_FEATURES:3] = angle_min
    highest_allowed[:, 2:N_SOLAR_FEATURES:3] = orientation_max
    lowest_allowed[:, 2:N_SOLAR_FEATURES:3] = orientation_min
    highest_allowed[:, -1] = N_WIND_MAX
    lowest_allowed[:, -1] = N_WIND_MIN


    last_generation = n_generations - 1
    best_gen = 0
    cost_temp = 1e20

    for generation in range(n_generations):

        if generation == n_generations - 20:
            genetic_algorithm.set_mutation(mutationPercentage / 2)
        elif generation == n_generations - 10:
            genetic_algorithm.set_mutation(mutationPercentage / 4)

        cost_array = np.zeros(group_size)

        for i in range(group_size):
            current_row = group_values[i]
            # selecting windturbine type

            wm_type = 4
            n_Turbines = int(current_row[-1])
            # run simulink
            energy_production,_= simulator.calc_total_power(current_row[:N_SOLAR_FEATURES],
                                                            list([n_Turbines, turbine_height]),
                                                            sp_efficiency)
            # run cost calculator
            sp_sm = np.sum(current_row[0:N_SOLAR_FEATURES:3])
            cost_array[i] = cost_calculator.calculate_cost(energy_production, sp_sm, wm_type, n_Turbines)

            #quit when gui calls stop
            if parent.stopped:
                break
        #quit when gui calls stop
        if parent.stopped:
            break
        best = genetic_algorithm.get_best(group_values, cost_array)
        
        if np.min(cost_array) < cost_temp:
            cost_temp = np.min(cost_array)
            best_gen = best

        event_data = [best_gen[0],generation]
        parent.gendone(event_data)

        # quit when done
        if generation == last_generation:
            parent.traindone(None)
            return best_gen
        # run genetic algorithm
        group_values = genetic_algorithm.generate_new_population(group_values, cost_array)
        # remove illegal values
        group_values = np.minimum(group_values, highest_allowed)
        group_values = np.maximum(group_values, lowest_allowed)


if __name__ == '__main__':
    
    cost_calculator = CostCalculator(160, 400, 6000, 1000000)
    

    my_loc = Location('volkel')
    turbine = Windturbine(4)

    sim = Simulator(my_loc, '2018', turbine)

    p_wind, e_wind = sim.calc_wind([4, 100])
    p_solar, e_solar = sim.calc_solar(Az=[0,0,0,0], Inc=[0,23,14,23], sp_area=[1000000,1000000,1000000,1000000])

    total_wind = np.sum(p_wind)
    total_solar = np.sum(p_solar)
    total = p_wind + p_solar

    stats = cost_calculator.get_stats(total, 4000000, 4, 4)

    print('Total wind: ' + str(total_wind))
    print('Total solar: ' + str(total_solar))


