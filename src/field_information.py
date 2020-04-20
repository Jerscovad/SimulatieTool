
"""
All fields that need information can be declared here.
The variable here needs to be the same as the name of the field that is refers to.

"""

def field_info(name):
    switcher={
            'wtn_min':'Minimum amount of turbines used while training for optimal configuration.',
            'wtn_max':'Maximum amount of turbines used while training for optimal configuration.',
            'turbine_height':'Height in meters to the center of the turbine rotor.',
            'terrain_factor':'Factor with which the surrounding terrain effects the wind turbine.',
            'demand':'Constand power demand in kW.',
            'generations':'Number of generations the algorithm has to achieve the optimal configuration. Increasing this will result is longer training but more accurate results.',
            'pool_size':'Number of configurations tried in each generation. Increasing this will result in longer training times but more variation thus better outcome after each generation.',
            'mutation_rate':'Percentage with which the algorithm varies each independant configuration. Avoid number smaller than 50 because this could lead to local minima.',
            'solar_panel_price':'Price of the solar panels in Euro per square meter. Increasing the price will lead to less solar panels used.',
            'wind_turbine_price':'Price of the wind turbine in Euro per kW. For this the maximum power of the turbine is used. Increasing the price will lead to less wind turbines used.',
            'storage_price':'Price of storage per kWh. Increasing the price will lead to less storage used.',
            'shortage_price':'Price of energy shortage per kWh. Calculated by subtracting the sum of the demand from the sum of the energy produced.',
            'surplus_price':'Price of energy surplus per kWh. Calculated by subtracting the sum of the demand from the sum of the energy produced.',
            'load_default':'Load the default values.',
            'save_default':'Save current values as default for future training sessions.',
            'sp_eff': 'The efficiency of the solar panel output.',
            'sp_area_min': 'Minimum area of solar panels in square meters.',
            'sp_area_max': 'Maximum area of solar panels in square meters.',
            'sp_ang_min': 'Lowest angle of solar panels. Range from 0 to 90 degrees. Angle above 90 or below 0 will produce unrealistic numbers.',
            'sp_ang_max': 'Highest angle of solar panels. Range from 0 to 90 degrees. Angle above 90 or below 0 will produce unrealistic numbers.',
            'sp_or_min': 'Solar panel minimum azimuth orientation. South = 0, North = -180, East = -90, West = 90. Range from -180 to 179.',
            'sp_or_max': 'Solar panel maximum azimuth orientation. South = 0, North = -180, East = -90, West = 90. Range from -180 to 179.'
         }
    return switcher.get(name,"No information for requested field")