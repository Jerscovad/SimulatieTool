import pandas as pd
import numpy as np
import os

class Location():
    """Class for getting location information"""
    def __init__(self, name):
        self.loc_data = pd.read_csv('Data' + os.sep + 'locations.csv', index_col=0, header=0)
        self.name = name.upper()
        self.latitude = self.loc_data.LAT[self.loc_data.NAME == self.name].values[0]
        self.longitude = self.loc_data.LON[self.loc_data.NAME == self.name].values[0]
        self.altitude = self.loc_data.ALT[self.loc_data.NAME == self.name].values[0]
        self.stn = self.loc_data.STN[self.loc_data.NAME == self.name].values[0]
        self.terrain = self.loc_data.Terrain[self.loc_data.NAME == self.name].values[0]
        self.years = self.loc_data.Years[self.loc_data.NAME == self.name].values[0]

    def get_years(self):
        perfect_years = ['1998', '1999', '2000', '2001', '2002',
                         '2003', '2004', '2005', '2006', '2007',
                         '2008', '2009', '2010', '2011', '2012',
                         '2013', '2014', '2015', '2016', '2017', '2018']
        loc_years = np.array([])

        for i in range(len(self.years)):
            if bool(int(self.years[i])):
                loc_years = np.append(loc_years,perfect_years[i])

        return loc_years
        
