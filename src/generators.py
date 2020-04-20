import numpy as np

class Windturbine():
    def __init__(self, wt_model):
        self.model= wt_model
        if (self.model == 1):
            self.power_curve = np.array([0, 0, 3, 130, 270, 400, 430, 500, 500, 0, 0])
            self.rotor_height = 25
            self.wind_curve = np.array([0, 3, 5, 7, 8, 9, 10, 12, 25, 25.01, 1000])
        elif (self.model == 2):
            self.power_curve = np.array([0, 0, 80, 400, 800, 1200, 1300, 1500, 1500, 0, 0])
            self.rotor_height = 85
            self.wind_curve = np.array([0, 3, 5, 7, 8, 9, 10, 12, 25, 25.01, 1000])
        elif (self.model == 3):
            self.power_curve = np.array([0, 0, 27, 1300, 2700, 4000, 4300, 5000, 5000, 0, 0])
            self.rotor_height = 124
            self.wind_curve = np.array([0, 3, 5, 7, 8, 9, 10, 12, 25, 25.01, 1000])
        elif (self.model== 4):
            self.power_curve = np.array([0, 0, 47, 111, 217, 375, 595, 889, 1266, 1736, 2311, 3000, 3000, 0, 0])
            self.rotor_height = 135
            self.wind_curve = np.array([0, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 25, 25.01, 1000])
        elif (self.model== 5):
            self.power_curve = np.array([0, 0, 47, 111, 217, 375, 595, 889, 1266, 1736, 2311, 3000, 3000, 0, 0])
            self.rotor_height = 100
            self.wind_curve = np.array([0, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 25, 25.01, 1000])

