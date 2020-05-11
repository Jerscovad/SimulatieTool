import numpy as np
import pandas as pd
from datetime import datetime
from windturbine import Windturbine
from location import Location
import time
import os

#remove warning filter after devide by zero is solved!
import warnings
warnings.filterwarnings("ignore")

KAPPA = 1.041  # for calculations in radians
IO = 1366.1  # solar constant(w/m^2)
NANO = 1e-9  # for conversion from nanoseconds
LSM = 15  # local standard time meridian


class Simulator():
    """Class for calculating irradiation"""

    def __init__(self, Location, year, Windturbine, latitude=None, longitude=None, terrain_factor=None, lsm=15):
        # variables from arguments
        self.location = Location
        if latitude:
            self.latitude = latitude
        else:
            self.latitude = self.location.latitude
        if longitude:
            self.longitude = longitude
        else:
            self.longitude = self.location.longitude
        if terrain_factor :
            self.terrain_factor = terrain_factor
        else:
            self.terrain_factor = self.location.terrain
        self.Windturbine = Windturbine

        # variables from data file
        file_name = 'Data'+ os.sep + self.location.name + os.sep + year + '.csv'
        self.import_data = pd.read_csv(file_name, index_col=0)
        self.ghi = self.import_data.iloc[:, 5].values
        self.dni = self.import_data.iloc[:, 7].values
        self.dates = self.import_data.iloc[:, 1].values

        if type(self.dates[0]) == str:
            self.doy = np.array([datetime.strptime(self.dates[i], '%Y-%m-%d').timetuple().tm_yday for i in range(0, len(self.dates))])
        else:
            self.doy = np.array([datetime.utcfromtimestamp(self.dates[i].astype(int) * NANO).timetuple().tm_yday for i in range(0, len(self.dates))])
        
        self.time = self.import_data.iloc[:, 2].values.astype(int)
        self.wind_speed = (self.import_data.iloc[:, 3].values) / 10
        self.temperature = (self.import_data.iloc[:, 4].values) / 10

    def calc_solar(self, Az=[0, 0, 0, 0], Inc=[15, 15, 15, 15], sp_area=[100, 100, 100, 100], sp_eff=16, gref=0):
        gamma = np.array(Az)
        beta = np.array(Inc)

        # calculation of sun positions                         
        day_angle = 2 * np.pi * (self.doy - 1) / 365
        decl = 23.442 * np.sin(np.deg2rad((360 / 365) * (self.doy + 284)))

        # equation of time 
        EQT = 229.18 * (0.0000075 + 0.001868 * np.cos(np.deg2rad(day_angle))
                        - 0.032077 * np.sin(np.deg2rad(day_angle)) - 0.014615 * np.cos(np.deg2rad(2 * day_angle))
                        - 0.040849 * np.sin(np.deg2rad(2 * day_angle)))

        # hour angle [deg] 
        h = 15 * ((self.longitude - LSM) * 4 / 60 + (self.time - 12 - 0.5 + EQT / 60))
        hai = np.round(np.sin(np.deg2rad(self.latitude)), 4) * np.round(np.sin(np.deg2rad(decl)), 4) + np.round(
            np.cos(np.deg2rad(self.latitude)), 4) * np.round(np.cos(np.deg2rad(decl)) * np.cos(np.deg2rad(h)), 4)

        # calculating DHI from GHI and DNI
        DHI = self.ghi - self.dni * hai
        DHI[DHI < 0] = 0

        sel = np.degrees(np.arcsin(hai))  # sel=solar elevation angle [deg]
        Zen = np.arccos(hai)  # Zen=solar zenith angle [radians!!]

        # Perez factors for calculation of circumsolar and horizon brightness coefficients
        f11 = np.array([-0.008, 0.130, 0.330, 0.568, 0.873, 1.132, 1.060, 0.678])
        f12 = np.array([0.588, 0.683, 0.487, 0.187, -0.392, -1.237, -1.600, -0.327])
        f13 = np.array([-0.062, -0.151, -0.221, -0.295, -0.362, -0.412, -0.3590, -0.2500])
        f21 = np.array([-0.0600, -0.0190, 0.0550, 0.1090, 0.2260, 0.2880, 0.2640, 0.1560])
        f22 = np.array([0.072, 0.066, -0.064, -0.152, -0.462, -0.823, -1.1270, -1.3770])
        f23 = np.array([-0.022, -0.029, -0.026, -0.014, 0.001, 0.056, 0.131, 0.2510])

        # determination of bin with eps
        s_bin = np.ones(len(self.time))  # bin 1 is overcast sky , bin 8 is clear sky
        Kzen3 = KAPPA * Zen ** 3

        eps = ((DHI + self.dni) / DHI + KAPPA * Zen ** 3) / (1 + KAPPA * Zen ** 3)

        s_bin[np.logical_and(eps >= 1.065, eps < 1.23)] = 2
        s_bin[np.logical_and(eps >= 1.23, eps < 1.5)] = 3
        s_bin[np.logical_and(eps >= 1.5, eps < 1.95)] = 4
        s_bin[np.logical_and(eps >= 1.95, eps < 2.8)] = 5
        s_bin[np.logical_and(eps >= 2.8, eps < 4.5)] = 6
        s_bin[np.logical_and(eps >= 4.5, eps < 6.2)] = 7
        s_bin[(eps >= 6.2)] = 8

        # calculation of relative air mass
        M = 1 / hai
        M[sel < 2] = 20

        ETR = IO * (1 + 0.033 * np.cos(np.deg2rad(2 * np.pi * self.doy)) / 365)  # [deg]

        Delta = (DHI * M) / ETR

        s_bin_int = s_bin.astype(int)

        F1 = f11[s_bin_int - 1] + Delta * f12[s_bin_int - 1] + Zen * f13[s_bin_int - 1]
        F1[F1 < 0] = 0
        F2 = f21[s_bin_int - 1] + Delta * f22[s_bin_int - 1] + Zen * f23[s_bin_int - 1]

        # determination of cos angle of incidence of tilted surface 
        #  cai= cos angle of incidence of Solar to surface = cos(teta)
        gamma_dim = gamma[np.newaxis, :]
        beta_dim = beta[np.newaxis, :]
        decl_dim = decl[:, np.newaxis]
        h_dim = h[:, np.newaxis]

        cai = np.array(np.sin(np.deg2rad(decl_dim)) * np.sin(np.deg2rad(self.latitude)) * np.cos(np.deg2rad(beta_dim))
                       - np.sin(np.deg2rad(decl_dim)) * np.cos(np.deg2rad(self.latitude)) * (
                               np.sin(np.deg2rad(beta_dim)) * np.cos(np.deg2rad(gamma_dim)))
                       + (np.cos(np.deg2rad(decl_dim)) * np.cos(np.deg2rad(h_dim))) * np.cos(
            np.deg2rad(self.latitude)) * np.cos(np.deg2rad(beta_dim))
                       + (np.cos(np.deg2rad(decl_dim)) * np.cos(np.deg2rad(h_dim))) * np.sin(
            np.deg2rad(self.latitude)) * (np.sin(np.deg2rad(beta_dim)) * np.cos(np.deg2rad(gamma_dim)))
                       + np.cos(np.deg2rad(decl_dim)) * np.sin(np.deg2rad(h_dim)) * (
                               np.sin(np.deg2rad(beta_dim)) * np.sin(np.deg2rad(gamma_dim))))

        # determination of the diffuse radiation on a tilted surface DTI, Perez 1990
        a = cai
        a[a < 0] = 0

        b = np.cos(Zen)
        b[b < 0.087] = 0.087

        # Adjust for broadcast operations
        b = b[:, np.newaxis]
        DHI_dim = DHI[:, np.newaxis]
        F1_dim = F1[:, np.newaxis]
        F2_dim = F2[:, np.newaxis]
        DNI_dim = self.dni[:, np.newaxis]

        c = (a / b) * F1_dim

        DTI = DHI_dim * (1 - F1_dim) * (1 + np.cos(np.deg2rad(beta_dim))) / 2 + c + F2_dim * np.sin(
            np.deg2rad(beta_dim))
        DTI[DTI < 0] = 0

        DSTI = cai * DNI_dim
        DSTI[DSTI < 0] = 0

        Rg = 0.5 * gref * (DHI_dim + DNI_dim) * (1 - np.cos(np.deg2rad(beta_dim)))

        GTI = DTI + DSTI + Rg

        individual_output = (GTI * (sp_eff / 100)) * sp_area

        total_output = np.sum(individual_output, axis=1)

        P_out = total_output / 1000  # kW

        """        
        Solar calculations according to Matlab script
        E = total_output/(3600)*10^-6

        for some reason matlab does not devide by 3600 resulting in the calculation
        having the same outcome as the one below

        """
        e_temp = total_output/1000 #kWh
        E_out = np.cumsum(e_temp)

        return P_out, E_out

    def calc_wind(self, wind_features):
        n_turbines = int(wind_features[0])
        rotor_height = int(wind_features[1])
        external_factors = (rotor_height / 10) ** self.terrain_factor

        in_values = self.wind_speed * external_factors

        excl = self.Windturbine.wind_curve[np.newaxis, :] - in_values[:, np.newaxis]
        abs_excl = np.abs(excl)

        index_1 = abs_excl.argmin(axis=1)
        index_2 = index_1 - 1
        index_2[excl[np.arange(in_values.shape[0]), index_1] < 0] += 2

        a_1 = self.Windturbine.wind_curve[index_1]
        a_2 = self.Windturbine.wind_curve[index_2]

        difference_1 = np.abs(a_1 - in_values)
        difference_2 = np.abs(a_2 - in_values)
        difference = difference_1 + difference_2

        value_1 = self.Windturbine.power_curve[index_1]
        value_2 = self.Windturbine.power_curve[index_2]

        P_out_single = (value_1 * difference_2 + value_2 * difference_1) / difference  # kW
        P_out = P_out_single * n_turbines  # kW

        E_out = np.cumsum(P_out)  # kWh

        return P_out, E_out

    def calc_total_power(self, solar_features, wind_features, sp_eff):
        surface_features = solar_features[0::3]
        angle_features = solar_features[1::3]
        orientation_features = solar_features[2::3]

        p_wind, e_wind  = self.calc_wind(wind_features)
        p_solar, e_solar= self.calc_solar(Az=orientation_features, Inc=angle_features, sp_area=surface_features, sp_eff=sp_eff)

        total_power = p_wind + p_solar
        total_energy = e_wind + e_solar

        return total_power, total_energy

if __name__ == '__main__':

    my_loc = Location('nen')
    turbine = Windturbine(4)

    sim = Simulator(my_loc, '2018', turbine)

    p_wind, e_wind = sim.calc_wind([1, 100])
    p_solar, e_solar = sim.calc_solar(Az=[-5,-10,10,5], Inc=[15,15,15,15], sp_area=[100,100,100,100])

    df = pd.DataFrame({'p_solar':p_solar,'e_solar':e_solar})
    print(df[:20])

