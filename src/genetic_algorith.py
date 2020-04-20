"""contains class to create new populations"""

import numpy as np
from copy import copy


class GeneticAlgorith():
    """class to create new populations"""
    def __init__(self, mutation_percentage_chance, max_mutation_percentage,
                 n_optimal_to_select, n_different_to_select, n_random_to_select, keep_best):
        self.set_mutation(mutation_percentage_chance)
        self.n_optimal_to_select = n_optimal_to_select
        self.n_different_to_select = n_different_to_select
        self.n_random_to_select = n_random_to_select
        self.keep_best = keep_best
        self.average_array = None

    def set_mutation(self, new_percentage):
        self.mutation_chance = new_percentage / 100
        self.max_mutation = 1 + (new_percentage / 100)
        self.min_mutation = 1 - (new_percentage / 100)

    def _mutate(self, population):
        chance = np.random.rand(*population.shape)
        mask = chance < self.mutation_chance
        mutation = np.random.rand(*population.shape) * (self.max_mutation - self.min_mutation) + self.min_mutation
        mutated = mutation * population
        population[mask] = mutated[mask]

    def _calculate_difference(self, array):
        difference_array = np.abs(self.average_array - array)
        mask = difference_array != 0
        difference_array[mask] = difference_array[mask] / np.maximum(
            np.abs(self.average_array[mask]),
            np.abs(array[mask]))
        return np.mean(difference_array)

    def _select_and_mate(self, population, cost):
        population_size, n_features = population.shape
        if population_size != cost.shape[0]:
            raise ValueError('population and cost should have the same length')
        # sort population by cost (low to high)
        population = population[cost.argsort()]
        # select fittest
        best_selected = population[:self.n_optimal_to_select]
        # get average values of fittest
        self.average_array = np.mean(best_selected, axis=0)
        # select remaining
        remaining = population[self.n_optimal_to_select:]
        differences = np.array(list(map(self._calculate_difference, remaining)))
        # sort remaining by difference (low to high)
        remaining = remaining[differences.argsort()]
        # select most different of the remaining
        different_selected = remaining[-self.n_different_to_select:]
        # select remaining again
        remaining = remaining[:-self.n_different_to_select]
        randomly_selected = remaining[np.random.choice(remaining.shape[0], self.n_random_to_select)]
        # get parents
        parents = np.concatenate((best_selected, different_selected, randomly_selected), axis=0)
        n_parents = parents.shape[0]
        # make new generation
        new_population = np.zeros_like(population)
        for i in range(population_size):
            # select parents
            parent1 = parents[np.random.randint(n_parents)]
            parent2 = parents[np.random.randint(n_parents)]
            # combine to make child
            child = copy(parent1)
            mask = np.random.rand(n_features) > 0.5
            child[mask] = parent2[mask]
            # assign child to new population
            new_population[i] = child
        if self.keep_best:
            new_population[0] = best_selected[0]
        return new_population

    def generate_new_population(self, population, cost):
        """make a new population using the old population(2d array) and the cost(1d array)"""
        new_population = self._select_and_mate(population, cost)
        if self.keep_best:
            best = new_population[0, :]
        self._mutate(new_population)
        if self.keep_best:
            new_population[0] = best
        return(new_population)
    
    def get_best(self, population, cost, n=1):
        population_size = population.shape[0]
        if population_size != cost.shape[0]:
            raise ValueError('population and cost should have the same length')
        if population_size < n:
            raise ValueError('n > population_size')
        # sort population by cost (low to high)
        population = population[cost.argsort()]
        # select fittest
        return population[:self.n_optimal_to_select]


# example code to test the algorithm
if __name__ == '__main__':
    genetic_algorithm = GeneticAlgorith(10, 50, 6, 2, 2, True)
    population = np.array([
        [0, 0],
        [0, 1],
        [0, 2],
        [0, 3],
        [0, 4],
        [0, 5],
        [0, 6],
        [0, 7],
        [0, 8],
        [0, 9],
        [1, 0],
        [1, 1],
        [1, 2],
        [1, 3],
        [1, 4],
        [1, 5],
        [1, 6],
        [1, 7],
        [1, 8],
        [1, 9],
        [2, 0],
        [2, 1],
        [2, 2],
        [2, 3],
        [2, 4],
        [2, 5],
        [2, 6],
        [2, 7],
        [2, 8],
        [2, 9],
        [3, 0],
        [3, 1],
        [3, 2],
        [3, 3],
        [3, 4],
        [3, 5],
        [3, 6],
        [3, 7],
        [3, 8],
        [3, 9],
        [4, 0],
        [4, 1],
        [4, 2],
        [4, 3],
        [4, 4],
        [4, 5],
        [4, 6],
        [4, 7],
        [4, 8],
        [4, 9],
        [5, 0],
        [5, 1],
        [5, 2],
        [5, 3],
        [5, 4],
        [5, 5],
        [5, 6],
        [5, 7],
        [5, 8],
        [5, 9],
        [6, 0],
        [6, 1],
        [6, 2],
        [6, 3],
        [6, 4],
        [6, 5],
        [6, 6],
        [6, 7],
        [6, 8],
        [6, 9],
        [7, 0],
        [7, 1],
        [7, 2],
        [7, 3],
        [7, 4],
        [7, 5],
        [7, 6],
        [7, 7],
        [7, 8],
        [7, 9],
        [8, 0],
        [8, 1],
        [8, 2],
        [8, 3],
        [8, 4],
        [8, 5],
        [8, 6],
        [8, 7],
        [8, 8],
        [8, 9],
        [9, 0],
        [9, 1],
        [9, 2],
        [9, 3],
        [9, 4],
        [9, 5],
        [9, 6],
        [9, 7],
        [9, 8],
        [9, 9],
    ], dtype=float)
    minimum = np.zeros_like(population)
    maximum = np.ones_like(population) * 100
    cost = np.array([l[0] - l[-1] for l in population], dtype=float)
    print(np.mean(cost))
    for i in range(20):
        population = genetic_algorithm.generate_new_population(population, cost)
        population = np.minimum(population, maximum)
        population = np.maximum(population, minimum)
        cost = np.array([l[0] - l[-1] for l in population], dtype=float)
        print(np.mean(cost))
    best = genetic_algorithm.get_best(population, cost, n=5)
    print('should reach [0, 100], but there is randomness involved')
    print(best)
