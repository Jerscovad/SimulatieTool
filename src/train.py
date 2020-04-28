
import numpy as np
import wx
import pandas as pd
from calculate_cost import CostCalculator
from genetic_algorithm import GeneticAlgorithm
from multiprocessing import Process, Value
from windturbine import Windturbine
from simulator import Simulator
from location import Location

class Trainer():
    """
    Class for training the Genetic Algorithm.
    """
    def __init__(self, parent, generations=100, group_size=100, n_configs=4, surface_min=0, 
                 surface_max=10000000, angle_min=0, angle_max=90, orientation_min=-180, 
                 orientation_max=180, mutation_percentage=150, turbines_min=0, turbines_max=10, 
                 turbine_height=100, cost_calculator=None, simulator=None, sp_eff=16):
        self.parent = parent
        self.generations = generations
        self.group_size = group_size
        self.n_solar_features = n_configs * 3
        self.surface_min = surface_min
        self.surface_max = surface_max
        self.angle_min = angle_min
        self.angle_max = angle_max
        self.orientation_min = orientation_min
        self.orientation_max = orientation_max
        self.turbines_min = turbines_min
        self.turbines_max = turbines_max
        self.turbine_height = turbine_height
        self.sp_eff = sp_eff
        self.simulator = simulator
        self.cost_calculator = cost_calculator
        self.genetic_algorithm = GeneticAlgorithm(mutation_percentage, 150, 6, 2, 2, True )
        self.stopped = False

    def train(self):
        solar_values = np.random.rand(self.group_size, self.n_solar_features)
        solar_values[:, 0::3] *= (self.surface_max - self.surface_min)
        solar_values[:, 0::3] += self.surface_min
        solar_values[:, 1::3] *= (self.angle_max - self.angle_min)
        solar_values[:, 1::3] += self.angle_min
        solar_values[:, 2::3] *= (self.orientation_max - self.orientation_min)
        solar_values[:, 2::3] += self.orientation_min
        wind_values = np.random.rand(self.group_size, 1) #only the number of turbines is trained so '1' value
        wind_values *= self.turbines_max
        wind_values += self.turbines_min
        group_values = np.concatenate((solar_values, wind_values), axis=1)  # concatenate on features

        # prepare min and max arrays to truncate values later
        highest_allowed = np.zeros_like(group_values)
        lowest_allowed = np.zeros_like(group_values)
        highest_allowed[:, 0:self.n_solar_features:3] = self.surface_max
        lowest_allowed[:, 0:self.n_solar_features:3] = self.surface_min
        highest_allowed[:, 1:self.n_solar_features:3] = self.angle_max
        lowest_allowed[:, 1:self.n_solar_features:3] = self.angle_min
        highest_allowed[:, 2:self.n_solar_features:3] = self.orientation_max
        lowest_allowed[:, 2:self.n_solar_features:3] = self.orientation_min
        highest_allowed[:, -1] = self.turbines_max
        lowest_allowed[:, -1] = self.turbines_min


        last_generation = self.generations - 1
        best_gen = 0
        cost_temp = 1e20

        for generation in range(self.generations):

            if generation == self.generations - 20:
                self.genetic_algorithm.set_mutation(self.mutation_percentage / 2)
            elif generation == self.generations - 10:
                self.genetic_algorithm.set_mutation(self.mutation_percentage / 4)

            cost_array = np.zeros(self.group_size)

            for i in range(self.group_size):
                current_row = group_values[i]
                n_turbines = int(current_row[-1])

                # run simulator
                energy_production,_= self.simulator.calc_total_power(current_row[:self.n_solar_features],
                                                                list([n_turbines, self.turbine_height]),
                                                                self.sp_eff)
                # run cost calculator
                sp_sm = np.sum(current_row[0:self.n_solar_features:3])
                cost_array[i] = cost_calculator.calculate_cost(energy_production, sp_sm, n_turbines)

                #quit when gui calls stop
                if self.stopped:
                    break
            #quit when gui calls stop
            if self.stopped:
                break
            best = self.genetic_algorithm.get_best(group_values, cost_array)
            
            if np.min(cost_array) < cost_temp:
                cost_temp = np.min(cost_array)
                best_gen = best

            if parent:
                event_data = [best_gen[0],generation]
                parent.gendone(event_data)

            # quit when done
            if generation == last_generation:
                if parent:
                    parent.traindone(None)
                return best_gen
            # run genetic algorithm
            group_values = self.genetic_algorithm.generate_new_population(group_values, cost_array)
            # remove illegal values
            group_values = np.minimum(group_values, highest_allowed)
            group_values = np.maximum(group_values, lowest_allowed)


if __name__ == '__main__':
    print('hi')
    params = {'generations':200, 'group_size':300,'n_configs':3,'surface_min':1,'surface_max':1000,'angle_min':10,'angle_max':40,'orientation_min':-90, 'orientation_max':90,'mutation_percentage':100, 'turbines_min':1,'turbines_max':7, 'turbine_height':90,'sp_eff':17}

    trainer = Trainer(None, **params, cost_calculator = None, simulator =None)

    print(trainer.sp_eff)
    print(trainer.surface_min)
