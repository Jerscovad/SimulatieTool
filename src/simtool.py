import wx
import sys
from windturbine import Windturbine
from simulator import Simulator
from train import Trainer
from field_information import field_info
import numpy as np
import pandas as pd
import os
import xlsxwriter as xlw
import threading
from costcalculator import CostCalculator
from location import Location
import matplotlib
matplotlib.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

WT_PATH = f'config{os.sep}turbines'

myEVT_SAVEDONE = wx.NewEventType()
EVT_SAVEDONE = wx.PyEventBinder(myEVT_SAVEDONE, 1)

myEVT_TRAINDONE = wx.NewEventType()
EVT_TRAINDONE = wx.PyEventBinder(myEVT_TRAINDONE, 1)

myEVT_GENDONE = wx.NewEventType()
EVT_GENDONE = wx.PyEventBinder(myEVT_GENDONE, 1)

MAX_PLOTS = 4 #increase or decrease depending on number of graphs

class GenDoneEvent(wx.PyCommandEvent):
    """
    Event for when a generation is done in training.
    """
    def __init__(self, etype, eid, data):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.data = data

class TrainDoneEvent(wx.PyCommandEvent):
    """
    Event for when a traingin is done.
    """
    def __init__(self, etype, eid, data):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.data = data

class SaveDoneEvent(wx.PyCommandEvent):
    """
    Event for when the FileWriter is done saving a file
    """
    def __init__(self, etype, eid, filename=None):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.filename = filename
    def GetName(self):
        return self.filename

class TrainWorker(threading.Thread):
    """
    Class for threading a Trainer object. Ensures GUI is not blocked
    """
    def __init__(self, parent, params):
        threading.Thread.__init__(self, daemon=True)
        self.parent = parent

        self.trainer = Trainer(self, **params)

    def run(self):
        self.trainer.train()

    def stop(self):
        self.trainer.stopped = True

    def gendone(self, data):
        evt = GenDoneEvent(myEVT_GENDONE, -1, data)
        wx.PostEvent(self.parent, evt)

    def traindone(self, info):
        evt = TrainDoneEvent(myEVT_TRAINDONE, -1, info)
        wx.PostEvent(self.parent, evt)

class FileWriter(threading.Thread):
    """
    Class for writing simulation/training data into a xlsx file.
    """
    def __init__(self, parent, path, location, year_choice, terrain_factor, latitude, 
                 longitude, windfeatures, solarfeatures, sp_eff, wt_type, sp_price, 
                 st_price, wt_price, short_price, surp_price, demand):

        threading.Thread.__init__(self, daemon=True)
        self.parent = parent
        self.path = path
        self.location = location
        self.year_choice = year_choice
        self.terrain_factor = terrain_factor
        self.latitude = latitude
        self.longitude = longitude
        self.windfeatures = windfeatures
        self.solarfeatures = solarfeatures
        self.sp_eff = sp_eff
        self.turbine_type = wt_type
        self.sp_price = sp_price
        self.wt_price = wt_price
        self.st_price = st_price
        self.short_price = short_price
        self.surp_price = surp_price
        self.demand = demand

    def run(self):

        sim = Simulator(self.location, self.year_choice, Windturbine(self.turbine_type),latitude=self.latitude,
                        longitude=self.longitude, terrain_factor=self.terrain_factor )
        P_wt,E_wt = sim.calc_wind(self.windfeatures)
        P_sp,E_sp = sim.calc_solar(Az=self.solarfeatures[2::3], Inc=self.solarfeatures[1::3], sp_area=self.solarfeatures[0::3], sp_eff=self.sp_eff)
        P_tot,E_tot = sim.calc_total_power(self.solarfeatures, self.windfeatures, self.sp_eff)

        data = {'P_wt':P_wt,'E_wt':E_wt, 'P_sp':P_sp, 'E_sp':E_sp, 'P_tot':P_tot,
                'E_tot':E_tot}
        dataAvg = {'P_wt':np.mean(np.reshape(P_wt[:8760], (365,24)), axis=1),
                   'E_wt':np.mean(np.reshape(E_wt[:8760], (365,24)), axis=1), 
                   'P_sp':np.mean(np.reshape(P_sp[:8760], (365,24)), axis=1), 
                   'E_sp':np.mean(np.reshape(E_sp[:8760], (365,24)), axis=1), 
                   'P_tot':np.mean(np.reshape(P_tot[:8760], (365,24)), axis=1), 
                   'E_tot':np.mean(np.reshape(E_tot[:8760], (365,24)), axis=1)}
        if self.demand:
            P_dem = np.array([self.demand for i in range(len(P_wt))])
            E_dem = np.cumsum(P_dem)
            data['P_dem'] = P_dem
            data['E_dem'] = E_dem
            dataAvg['P_dem'] =np.mean(np.reshape(P_dem[:8760], (365,24)), axis=1)
            dataAvg['E_dem'] =np.mean(np.reshape(E_dem[:8760], (365,24)), axis=1)

        calculator = CostCalculator(self.sp_price, self.st_price, self.demand, self.short_price, self.wt_price, 
                 self.surp_price, train_by_price=True, windturbine=Windturbine(self.turbine_type))
        stats = calculator.get_stats(P_tot, np.sum(self.solarfeatures[0::3]), self.windfeatures[0])

        self.write_data(data, dataAvg,stats)

        evt = SaveDoneEvent(myEVT_SAVEDONE, -1, filename=self.path)
        wx.PostEvent(self.parent, evt)

    def write_data(self, data, dataAvg, stats):
        
        data_file = xlw.Workbook(self.path)
        bold = data_file.add_format({'bold': True})
        money = data_file.add_format({'num_format': '€#,##0'})

        parametersheet = data_file.add_worksheet('Input parameters')

        parametersheet.write('B1', 'Place', bold)
        parametersheet.write('C1', self.location.name)
        parametersheet.write('B2', 'Year', bold)
        parametersheet.write('C2', self.year_choice)
        parametersheet.write('B4', 'Latitude', bold)
        parametersheet.write('C4', self.latitude)
        parametersheet.write('B5', 'Longitude', bold)
        parametersheet.write('C5', self.longitude)
        parametersheet.write('B6', 'Terrain factor', bold)
        parametersheet.write('C6', self.terrain_factor)
        parametersheet.write('B7', 'N Windturbines', bold)
        parametersheet.write('C7', self.windfeatures[0])
        parametersheet.write('B8', 'Tubrine type', bold)
        parametersheet.write('C8', self.turbine_type)
        parametersheet.write('B9', 'Rotor height', bold)
        parametersheet.write('C9', self.windfeatures[1])
        parametersheet.write('B11', 'Sp Surface 1', bold)
        parametersheet.write('C11', self.solarfeatures[0])
        parametersheet.write('B12', 'Sp Angle 1', bold)
        parametersheet.write('C12', self.solarfeatures[1])
        parametersheet.write('B13', 'Sp Orientation 1', bold)
        parametersheet.write('C13', self.solarfeatures[2])
        parametersheet.write('B14', 'Sp Surface 2', bold)
        parametersheet.write('C14', self.solarfeatures[3])
        parametersheet.write('B15', 'Sp Angle 2', bold)
        parametersheet.write('C15', self.solarfeatures[4])
        parametersheet.write('B16', 'Sp Orientation 2', bold)
        parametersheet.write('C16', self.solarfeatures[5])
        parametersheet.write('B17', 'Sp Surface 3', bold)
        parametersheet.write('C17', self.solarfeatures[6])
        parametersheet.write('B18', 'Sp Angle 3', bold)
        parametersheet.write('C18', self.solarfeatures[7])
        parametersheet.write('B19', 'Sp Orientation 3', bold)
        parametersheet.write('C19', self.solarfeatures[8])
        parametersheet.write('B20', 'Sp Surface 4', bold)
        parametersheet.write('C20', self.solarfeatures[9])
        parametersheet.write('B21', 'Sp Angle 4', bold)
        parametersheet.write('C21', self.solarfeatures[10])
        parametersheet.write('B22', 'Sp Orientation 4', bold)
        parametersheet.write('C22', self.solarfeatures[11])
        parametersheet.write('B23', 'Sp Efficiency', bold)
        parametersheet.write('C23', self.sp_eff)
        parametersheet.write('B25', 'Solar price', bold)
        parametersheet.write('C25', self.sp_price, money)
        parametersheet.write('B26', 'Turbine price', bold)
        parametersheet.write('C26', self.wt_price, money)
        parametersheet.write('B27', 'Storage price', bold)
        parametersheet.write('C27', self.st_price, money)
        if self.surp_price:
            parametersheet.write('B28', 'Surplus price', bold)
            parametersheet.write('C28', self.surp_price, money)
            parametersheet.write('B29', 'Shortage price', bold)
            parametersheet.write('C29', self.short_price, money)

        if self.demand:
            parametersheet.write('B31', 'Demand', bold)
            parametersheet.write('C31', self.demand)

        cost_sheet = data_file.add_worksheet('Cost')

        cost_sheet.write('B2', 'Input prices', bold)
        cost_sheet.write('B3', 'Solar cost per m^2', bold)
        cost_sheet.write('C3', self.sp_price, money)
        cost_sheet.write('B4', 'Turbine price per kW', bold)
        cost_sheet.write('C4', self.wt_price, money)
        cost_sheet.write('B5', 'Storage price per kWh', bold)
        cost_sheet.write('C5', self.st_price, money)

        cost_sheet.write('B7', 'Cost output', bold)
        cost_sheet.write('B8', 'Total cost', bold)
        cost_sheet.write('C8', stats['cost'],money)
        cost_sheet.write('B9', 'Solar cost', bold)
        cost_sheet.write('C9', stats['solar_cost'], money)
        cost_sheet.write('B10', 'Windturbine cost', bold)
        cost_sheet.write('C10', stats['wind_cost'], money)
        cost_sheet.write('B11', 'Storage cost', bold)
        cost_sheet.write('C11', stats['storage_cost'], money)

        cost_chart = data_file.add_chart({'type':'pie'})

        cost_chart.add_series({'name': 'Costs',
                               'categories': '=Cost!$B$9:$B$11',
                               'values':     '=Cost!$C$9:$C$11',
                               'points': [{'fill': {'color': '#FF9900'}},
                                          {'fill': {'color': '#4287F5'}},
                                          {'fill': {'color': '#23BF00'}},],})

        cost_sheet.insert_chart('F2', cost_chart)

        datasheet = data_file.add_worksheet('Output')

        datasheet.write('B1', 'Hourly output', bold)
        datasheet.write('B2', 'Solar Power', bold)
        datasheet.write_column('B3', data['P_sp'])
        datasheet.write('C2', 'Solar Energy', bold)
        datasheet.write_column('C3', data['E_sp'])
        datasheet.write('D2', 'Wind power', bold)
        datasheet.write_column('D3', data['P_wt'])
        datasheet.write('E2', 'Wind Energy', bold)
        datasheet.write_column('E3' ,data['E_wt'])
        datasheet.write('F2', 'Total Power', bold)
        datasheet.write_column('F3', data['P_tot'])
        datasheet.write('G2', 'Total Energy', bold)
        datasheet.write_column('G3', data['E_tot'])
        if self.demand:
            datasheet.write('H2', 'Demand', bold)
            datasheet.write_column('H3', data['P_dem'])
            datasheet.write('I2', 'Demand', bold)
            datasheet.write_column('I3', data['E_dem'])

        datasheet.write('K1', 'Daily output', bold)
        datasheet.write('K2', 'Solar Power', bold)
        datasheet.write_column('K3', dataAvg['P_sp'])
        datasheet.write('L2', 'Solar Energy', bold)
        datasheet.write_column('L3', dataAvg['E_sp'])
        datasheet.write('M2', 'Wind power', bold)
        datasheet.write_column('M3', dataAvg['P_wt'])
        datasheet.write('N2', 'Wind Energy', bold)
        datasheet.write_column('N3', dataAvg['E_wt'])
        datasheet.write('O2', 'Total Power', bold)
        datasheet.write_column('O3', dataAvg['P_tot'])
        datasheet.write('P2', 'Total Energy', bold)
        datasheet.write_column('P3', dataAvg['E_tot'])
        if self.demand:
            datasheet.write('Q2', 'Demand', bold)
            datasheet.write_column('Q3', dataAvg['P_dem'])
            datasheet.write('R2', 'Demand', bold)
            datasheet.write_column('R3', dataAvg['E_dem'])

        # Create worksheets holding different charts
        chartsheet_1 = data_file.add_worksheet('Power graphs 1')
        chartsheet_2 = data_file.add_worksheet('Power graphs 2')
        chartsheet_3 = data_file.add_worksheet('Energy graphs 1')
        chartsheet_4 = data_file.add_worksheet('Energy graphs 2')

        # Create charts 
        p_totchart = data_file.add_chart({'type':'line'})
        p_solarchart = data_file.add_chart({'type':'line'})
        p_windchart = data_file.add_chart({'type':'line'})
        p_allchart = data_file.add_chart({'type':'line'})

        # Add the data to corresponding chart
        p_totchart.add_series({'name': 'combined power', 'values': 'Output!$F$3:$F$8762', 'line' :{'color': '#23BF00', 'width': 2,'transparency': 50}})
        p_solarchart.add_series({'name': 'solar power', 'values': 'Output!$B$3:$B$8762', 'line' :{'color': '#FF9900', 'width': 2,'transparency': 50}})
        p_windchart.add_series({'name': 'wind power', 'values': 'Output!$D$3:$D$8762', 'line' :{'color': '#4287F5', 'width': 2,'transparency': 50}})
        p_allchart.add_series({'name': 'solar power', 'values': 'Output!$B$3:$B$8762', 'line' :{'color': '#FF9900', 'width': 2,'transparency': 50}})
        p_allchart.add_series({'name': 'wind power', 'values': 'Output!$D$3:$D$8762', 'line' :{'color': '#4287F5', 'width': 2,'transparency': 50}})
        p_allchart.add_series({'name': 'total power', 'values': 'Output!$F$3:$F$8762', 'line' :{'color': '#23BF00', 'width': 2,'transparency': 50}})

        # If there's a demand variable add it
        if self.demand:
            p_totchart.add_series({'name': 'demand', 'values': 'Output!$H$3:$H$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})
            p_solarchart.add_series({'name': 'demand', 'values': 'Output!$H$3:$H$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})
            p_windchart.add_series({'name': 'demand', 'values': 'Output!$H$3:$H$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})
            p_allchart.add_series({'name': 'demand', 'values': 'Output!$H$3:$H$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})

        # Set chart properties
        p_totchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        p_totchart.set_y_axis({'name': 'Power in kW', 'interval_unit': '1000'})
        p_totchart.set_title({'name': 'Combined solar & wind power'})
        p_solarchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        p_solarchart.set_y_axis({'name': 'Power in kW', 'interval_unit': '1000'})
        p_solarchart.set_title({'name':'Solar power'})
        p_windchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        p_windchart.set_y_axis({'name': 'Power in kW', 'interval_unit': '1000'})
        p_windchart.set_title({'name': 'Wind power'})
        p_allchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        p_allchart.set_y_axis({'name': 'Power in kW', 'interval_unit': '1000'})
        p_allchart.set_title({'name': 'Split power'})    
        
        # Insert the charts into the sheet
        chartsheet_1.insert_chart('B2', p_totchart, {'x_scale': 20, 'y_scale': 2})
        chartsheet_1.insert_chart('B38', p_solarchart, {'x_scale': 20, 'y_scale': 2})
        chartsheet_1.insert_chart('B74', p_windchart, {'x_scale':20, 'y_scale': 2})
        chartsheet_1.insert_chart('B110', p_allchart, {'x_scale': 20, 'y_scale': 2})

        # Create charts
        p_tot_avgchart = data_file.add_chart({'type':'line'})
        p_sol_avgchart = data_file.add_chart({'type':'line'})
        p_wind_avgchart = data_file.add_chart({'type':'line'})
        p_all_avgchart = data_file.add_chart({'type':'line'})

        # Add the values to corresponding charts
        p_tot_avgchart.add_series({'name':'combined power', 'values':'Output!$O$3:$O$367', 'line':{'color':'#23BF00', 'width': 2, 'transparency': 50}})
        p_sol_avgchart.add_series({'name':'solar power', 'values':'Output!$K$3:$K$367', 'line':{'color':'#FF9900','width':2,'transparency':50}})
        p_wind_avgchart.add_series({'name':'wind power', 'values':'Output!$M$3:$M$367', 'line':{'color':'#4287F5','width':2,'transparency':50}})
        p_all_avgchart.add_series({'name':'solar power', 'values':'Output!$K$3:$K$367', 'line':{'color':'#FF9900','width':2,'transparency':50}})
        p_all_avgchart.add_series({'name':'wind power', 'values':'Output!$M$3:$M$367', 'line':{'color':'#4287F5', 'width': 2, 'transparency': 50}})
        p_all_avgchart.add_series({'name':'combined power', 'values':'Output!$O$3:$O$367', 'line':{'color':'#23BF00', 'width': 2, 'transparency': 50}})        

        # If there's a demand variabeble, ad it to the charts
        if self.demand:
            p_sol_avgchart.add_series({'name':'demand', 'values':'Output!$Q$3:$Q$367', 'line': {'color':'red', 'width':2}})
            p_tot_avgchart.add_series({'name':'demand', 'values':'Output!$Q$3:$Q$367', 'line':{'color':'red', 'width': 2}})
            p_wind_avgchart.add_series({'name':'demand', 'values':'Output!$Q$3:$Q$367', 'line': {'color':'red', 'width':2}})
            p_all_avgchart.add_series({'name':'demand', 'values':'Output!$Q$3:$Q$367', 'line': {'color':'red', 'width':2}})
        # Set the chart axis and title properties
        p_tot_avgchart.set_x_axis({'name': 'Days','interval_unit': '10'})
        p_tot_avgchart.set_y_axis({'name': 'Power','interval_unit': '1000'})
        p_tot_avgchart.set_title({'name':'Combined solar & wind power'})
        p_sol_avgchart.set_x_axis({'name':'Days', 'interva;_unit': '10'})
        p_sol_avgchart.set_y_axis({'name':'Power', 'interval_unit': '1000'})
        p_sol_avgchart.set_title({'name':'Solar power'})
        p_wind_avgchart.set_x_axis({'name':'Days', 'interva;_unit': '10'})
        p_wind_avgchart.set_y_axis({'name':'Power', 'interval_unit': '1000'})
        p_wind_avgchart.set_title({'name':'Wind power'})
        p_all_avgchart.set_x_axis({'name':'Days', 'interva;_unit': '10'})
        p_all_avgchart.set_y_axis({'name':'Power', 'interval_unit': '1000'})
        p_all_avgchart.set_title({'name':'Split power'})
        
        # Insert the charts into the sheet
        chartsheet_2.insert_chart('B2', p_tot_avgchart,{'x_scale': 4, 'y_scale':2})
        chartsheet_2.insert_chart('B38', p_sol_avgchart,{'x_scale':4, 'y_scale':2})
        chartsheet_2.insert_chart('B74', p_wind_avgchart,{'x_scale':4, 'y_scale':2})
        chartsheet_2.insert_chart('B110', p_all_avgchart,{'x_scale':4, 'y_scale':2})

        """Do the same for energy data"""

        e_totchart = data_file.add_chart({'type':'line'})
        e_solarchart = data_file.add_chart({'type':'line'})
        e_windchart = data_file.add_chart({'type':'line'})
        e_allchart = data_file.add_chart({'type':'line'})
        

        # Add the data to corresponding chart
        e_totchart.add_series({'name': 'combined energy', 'values': 'Output!$G$3:$G$8762', 'line' :{'color': '#23BF00', 'width': 2,'transparency': 50}})
        e_solarchart.add_series({'name': 'solar energy', 'values': 'Output!$C$3:$C$8762', 'line' :{'color': '#FF9900', 'width': 2,'transparency': 50}})
        e_windchart.add_series({'name': 'wind energy', 'values': 'Output!$E$3:$E$8762', 'line' :{'color': '#4287F5', 'width': 2,'transparency': 50}})
        e_allchart.add_series({'name': 'solar energy', 'values': 'Output!$C$3:$C$8762', 'line' :{'color': '#FF9900', 'width': 2,'transparency': 50}})
        e_allchart.add_series({'name': 'wind energy', 'values': 'Output!$E$3:$E$8762', 'line' :{'color': '#4287F5', 'width': 2,'transparency': 50}})
        e_allchart.add_series({'name': 'combined energy', 'values': 'Output!$G$3:$G$8762', 'line' :{'color': '#23BF00', 'width': 2,'transparency': 50}})

        # If there's a demand variable add it
        if self.demand:
            e_totchart.add_series({'name': 'demand', 'values': 'Output!$I$3:$I$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})
            e_solarchart.add_series({'name': 'demand', 'values': 'Output!$I$3:$I$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})
            e_windchart.add_series({'name': 'demand', 'values': 'Output!$I$3:$I$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})
            e_allchart.add_series({'name': 'demand', 'values': 'Output!$I$3:$I$8762', 'line' :{'color': 'red', 'width': 2,'transparency': 50}})

        # Set chart properties
        e_totchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        e_totchart.set_y_axis({'name': 'energy in kWh', 'interval_unit': '1000'})
        e_totchart.set_title({'name': 'Combined solar & wind energy'})
        e_solarchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        e_solarchart.set_y_axis({'name': 'energy in kWh', 'interval_unit': '1000'})
        e_solarchart.set_title({'name':'Solar energy'})
        e_windchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        e_windchart.set_y_axis({'name': 'energy in kWh', 'interval_unit': '1000'})
        e_windchart.set_title({'name': 'Wind energy'})
        e_allchart.set_x_axis({'name': 'Hours', 'interval_unit': '100'})
        e_allchart.set_y_axis({'name': 'energy in kWh', 'interval_unit': '1000'})
        e_allchart.set_title({'name': 'Split energy'})    
        
        # Insert the charts into the sheet
        chartsheet_3.insert_chart('B2', e_totchart, {'x_scale': 8, 'y_scale': 2})
        chartsheet_3.insert_chart('B38', e_solarchart, {'x_scale': 8, 'y_scale': 2})
        chartsheet_3.insert_chart('B74', e_windchart, {'x_scale':8, 'y_scale': 2})
        chartsheet_3.insert_chart('B110', e_allchart, {'x_scale': 8, 'y_scale': 2})

        # Create charts
        e_tot_avgchart = data_file.add_chart({'type':'line'})
        e_sol_avgchart = data_file.add_chart({'type':'line'})
        e_wind_avgchart = data_file.add_chart({'type':'line'})
        e_all_avgchart = data_file.add_chart({'type':'line'})

        # Add the values to corresponding charts
        e_tot_avgchart.add_series({'name':'combined energy', 'values':'Output!$P$3:$P$367', 'line':{'color':'#23BF00', 'width': 2, 'transparency': 50}})
        e_sol_avgchart.add_series({'name':'solar energy', 'values':'Output!$L$3:$L$367', 'line':{'color':'#FF9900','width':2,'transparency':50}})
        e_wind_avgchart.add_series({'name':'wind energy', 'values':'Output!$N$3:$N$367', 'line':{'color':'#4287F5','width':2,'transparency':50}})
        e_all_avgchart.add_series({'name':'solar energy', 'values':'Output!$L$3:$L$367', 'line':{'color':'#FF9900','width':2,'transparency':50}})
        e_all_avgchart.add_series({'name':'wind energy', 'values':'Output!$N$3:$N$367', 'line':{'color':'#4287F5', 'width': 2, 'transparency': 50}})
        e_all_avgchart.add_series({'name':'combined energy', 'values':'Output!$P$3:$P$367', 'line':{'color':'#23BF00', 'width': 2, 'transparency': 50}})        

        # If there's a demand variabeble, ad it to the charts
        if self.demand:
            e_sol_avgchart.add_series({'name':'demand', 'values':'Output!$R$3:$R$367', 'line': {'color':'red', 'width':2}})
            e_tot_avgchart.add_series({'name':'demand', 'values':'Output!$R$3:$R$367', 'line':{'color':'red', 'width': 2}})
            e_wind_avgchart.add_series({'name':'demand', 'values':'Output!$R$3:$R$367', 'line': {'color':'red', 'width':2}})
            e_all_avgchart.add_series({'name':'demand', 'values':'Output!$R$3:$R$367', 'line': {'color':'red', 'width':2}})
        # Set the chart axis and title properties
        e_tot_avgchart.set_x_axis({'name': 'Days','interval_unit': '10'})
        e_tot_avgchart.set_y_axis({'name': 'energy in kWh','interval_unit': '1000'})
        e_tot_avgchart.set_title({'name':'Combined solar & wind energy'})
        e_sol_avgchart.set_x_axis({'name':'Days', 'interva;_unit': '10'})
        e_sol_avgchart.set_y_axis({'name':'energy in kWh', 'interval_unit': '1000'})
        e_sol_avgchart.set_title({'name':'Solar energy'})
        e_wind_avgchart.set_x_axis({'name':'Days', 'interva;_unit': '10'})
        e_wind_avgchart.set_y_axis({'name':'energy in kWh', 'interval_unit': '1000'})
        e_wind_avgchart.set_title({'name':'Wind energy'})
        e_all_avgchart.set_x_axis({'name':'Days', 'interva;_unit': '10'})
        e_all_avgchart.set_y_axis({'name':'energy in kWh', 'interval_unit': '1000'})
        e_all_avgchart.set_title({'name':'Split energy'})
        
        # Insert the charts into the sheet
        chartsheet_4.insert_chart('B2', e_tot_avgchart,{'x_scale': 4, 'y_scale':2})
        chartsheet_4.insert_chart('B38', e_sol_avgchart,{'x_scale':4, 'y_scale':2})
        chartsheet_4.insert_chart('B74', e_wind_avgchart,{'x_scale':4, 'y_scale':2})
        chartsheet_4.insert_chart('B110', e_all_avgchart,{'x_scale':4, 'y_scale':2})

        # Close file properly
        data_file.close()

class SimTab(wx.Panel):
    """
    Tab enclosing the simulation. Used for single simulations using specific inputs.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # Populate the locations list with all available locations
        self.locations = [i.lower().capitalize() for i in pd.read_csv(f'Data{os.sep}locations.csv',index_col=0,header=0).NAME.values]
        self.location_obj = None # Object containing all location data
        self.location = None # Just the location name

        self.years = ['0000'] # Placeholder for windows

        # Positional coords
        self.latitude = 0
        self.longitude = 0

        # Default prices
        self.sp_price = 160
        self.wt_price = 1070
        self.st_price = 400

        # Default configurations
        self.sp_area_1 = 10000
        self.sp_area_2 = 10000
        self.sp_area_3 = 10000
        self.sp_area_4 = 10000
        self.sp_or_1 = -5
        self.sp_or_2 = -10
        self.sp_or_3 = 10
        self.sp_or_4 = 5
        self.sp_ang_1 = 15
        self.sp_ang_2 = 15
        self.sp_ang_3 = 15
        self.sp_ang_4 = 15
        self.sp_eff = 16

        self.wt_height = 100
        self.n_wt = 7
        self.terrain_factor = 0

        # Iterator for cycling graphs
        self.plot_iter = 0

        # Variables holding the power and energy outputs
        self.solar_power = None
        self.wind_power = None
        self.total_power = None
        self.solar_energy = None
        self.wind_energy = None
        self.total_energy = None

        # REMOVE!
        self.demand = None
        self.demand_input = 6000

        self.power_surplus = 0
        self.power_shortage = 0
        self.power_storage = 0

        self.cost_calculator = None
        self.simulator = None
    
        # Cost output variables
        self.sol_cost = 0
        self.win_cost = 0 
        self.stor_cost = 0 

        vbox = wx.BoxSizer(wx.VERTICAL)

        locbox = wx.StaticBox(self, -1, 'Location')
        solbox = wx.StaticBox(self, -1, 'Solar options')
        winbox = wx.StaticBox(self, -1, 'Windturbine options')
        pricebox = wx.StaticBox(self, -1, 'Cost options')
        canvasbox = wx.StaticBox(self, -1, 'Graph')

        loc_sizer = wx.StaticBoxSizer(locbox, wx.VERTICAL)
        sol_sizer = wx.StaticBoxSizer(solbox, wx.VERTICAL)
        win_sizer = wx.StaticBoxSizer(winbox, wx.VERTICAL)
        price_sizer = wx.StaticBoxSizer(pricebox, wx.VERTICAL)
        canvas_sizer = wx.StaticBoxSizer(canvasbox, wx.VERTICAL)

        head_sizer = wx.BoxSizer(wx.HORIZONTAL)

        left_head_sizer = wx.BoxSizer(wx.VERTICAL)
        middle_head_sizer = wx.BoxSizer(wx.VERTICAL)

        hloc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hsol_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hwin_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hname_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hpriceSizer = wx.BoxSizer(wx.HORIZONTAL)

        loc_grid = wx.FlexGridSizer(2, 2, 10, 10)
        sol_grid = wx.FlexGridSizer(4, 5, 10, 10)
        win_grid = wx.FlexGridSizer(2, 4, 10, 10)
        price_grid = wx.FlexGridSizer(3, 2, 10, 10)

        self.places = wx.Choice(self, wx.ID_ANY, choices=self.locations)
        self.places.SetSelection(0)
        self.year_choice = wx.Choice(self, wx.ID_ANY, choices=self.years)

        self.lat_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.latitude}')
        self.lon_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.longitude}')

        lat_txt = wx.StaticText(self, wx.ID_ANY, 'Latitude ')
        lon_txt = wx.StaticText(self, wx.ID_ANY, 'Longitude ')

        sp_price_txt = wx.StaticText(self, wx.ID_ANY, 'Solar panel (€/m²) ')
        self.sp_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_price}')
        wt_price_txt = wx.StaticText(self, wx.ID_ANY, 'Wind turbine (€/kWh) ')
        self.wt_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.wt_price}')
        st_price_txt = wx.StaticText(self, wx.ID_ANY, 'Storage (€/kWh) ')
        self.st_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.st_price}')

        sp_eff_text = wx.StaticText(self, wx.ID_ANY, 'Panel efficiency(%) ')
        self.sp_eff_field = wx.TextCtrl(self, wx.ID_ANY, value = f'{self.sp_eff}')
        area_txt = wx.StaticText(self, wx.ID_ANY, 'Surface ')
        self.area_field1 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_area_1}')
        self.area_field2 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_area_2}')
        self.area_field3 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_area_3}')
        self.area_field4 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_area_4}')

        angle_txt = wx.StaticText(self, wx.ID_ANY, 'Angle ')
        self.angle_field1 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_ang_1}')
        self.angle_field2 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_ang_2}')
        self.angle_field3 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_ang_3}')
        self.angle_field4 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_ang_4}')

        or_txt = wx.StaticText(self, wx.ID_ANY, 'Orientation ')
        self.or_field1 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_or_1}')
        self.or_field2 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_or_2}')
        self.or_field3 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_or_3}')
        self.or_field4 = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_or_4}')

        nwt_txt = wx.StaticText(self, wx.ID_ANY, 'Number of turbines ')
        self.nwt_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.n_wt}')
        wth_txt = wx.StaticText(self, wx.ID_ANY, 'Turbine height ')
        self.wth_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.wt_height}')
        ter_txt = wx.StaticText(self, wx.ID_ANY, 'Terrain factor ')
        self.ter_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.terrain_factor}')
        wt_type_txt = wx.StaticText(self, wx.ID_ANY, 'Type: ')
        self.wt_type_choice = wx.Choice(self, wx.ID_ANY, choices=[os.path.splitext(n)[0] for n in os.listdir(WT_PATH) if '.csv' in n])

        self.save_button = wx.Button(self, wx.ID_ANY, label='Save simulation')
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_button_clicked)

        self.places.Bind(wx.EVT_CHOICE, self.on_location_picked)

        self.area_field1.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.area_field2.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.area_field3.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.area_field4.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.or_field1.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.or_field2.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.or_field3.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.or_field4.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.angle_field1.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.angle_field2.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.angle_field3.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.angle_field4.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.sp_eff_field.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.lat_field.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.lon_field.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.ter_field.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.wth_field.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        self.nwt_field.Bind(wx.EVT_TEXT, self.on_fieldbox_changed)
        
        self.nextgraph_button = wx.Button(self, label='>')
        self.previousgraph_button = wx.Button(self, label='<')
        self.simulate_button = wx.Button(self, label='Simulate')
        self.nextgraph_button.Bind(wx.EVT_BUTTON, self.on_next_clicked)
        self.previousgraph_button.Bind(wx.EVT_BUTTON, self.on_prev_clicked)
        self.simulate_button.Bind(wx.EVT_BUTTON, self.on_simulate_clicked)
        
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)

        graph_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        graph_button_sizer.AddMany([(self.previousgraph_button, 0, wx.ALL), (self.nextgraph_button, 0, wx.ALL),
                                    (self.simulate_button, 0, wx.ALL), (0, 0, 1),(self.save_button, 0, wx.ALL)])
        canvas_sizer.Add(graph_button_sizer, 0, wx.ALL|wx.EXPAND, 2)
        canvas_sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)

        self.Bind(EVT_SAVEDONE, self.on_savedone)

        hloc_sizer.AddMany([(self.places, 0, wx.ALL, 2), (self.year_choice, 0, wx.ALL, 2)])
        

        loc_grid.AddMany([(lat_txt, 0, wx.ALL, 2), (self.lat_field, 0, wx.ALL, 2), 
                         (lon_txt, 0, wx.ALL, 2), (self.lon_field, 0, wx.ALL, 2)])

        price_grid.AddMany([(sp_price_txt, 0, wx.ALL, 2), (self.sp_price_field, 0, wx.ALL, 2),
                            (wt_price_txt, 0, wx.ALL, 2), (self.wt_price_field, 0, wx.ALL, 2),
                            (st_price_txt, 0, wx.ALL, 2), (self.st_price_field, 0, wx.ALL, 2)])

        sol_grid.AddMany([(area_txt, 0, wx.ALL, 2), (self.area_field1, 0, wx.ALL, 2),
                          (self.area_field2, 0, wx.ALL, 2), (self.area_field3, 0, wx.ALL, 2),
                          (self.area_field4, 0, wx.ALL, 2), (angle_txt, 0, wx.ALL, 2),
                          (self.angle_field1, 0, wx.ALL, 2), (self.angle_field2, 0, wx.ALL, 2),
                          (self.angle_field3, 0, wx.ALL, 2), (self.angle_field4, 0, wx.ALL, 2),
                          (or_txt, 0, wx.ALL, 2), (self.or_field1, 0, wx.ALL, 2),
                          (self.or_field2, 0, wx.ALL, 2), (self.or_field3, 0, wx.ALL, 2),
                          (self.or_field4, 0, wx.ALL, 2), (sp_eff_text, 0, wx.ALL, 2),
                          (self.sp_eff_field, 0, wx.ALL, 2)])
        
        hsol_sizer.Add(sol_grid, 0, wx.ALL, 2)

        win_grid.AddMany([(nwt_txt, 0, wx.ALL, 2), (self.nwt_field, 0, wx.ALL, 2),
                          (wth_txt, 0, wx.ALL, 2), (self.wth_field, 0, wx.ALL, 2),
                          (ter_txt, 0, wx.ALL, 2), (self.ter_field, 0, wx.ALL, 2),
                          (wt_type_txt, 0 , wx.ALL, 2), (self.wt_type_choice, 0, wx.ALL, 2)])

        hwin_sizer.Add(win_grid, 0, wx.ALL, 2)

        loc_sizer.Add(hloc_sizer, 0 , wx.ALL, 2)
        loc_sizer.Add(loc_grid, 0 , wx.ALL, 2)
        price_sizer.Add(price_grid, 0, wx.ALL, 2)
        
        sol_sizer.Add(hsol_sizer, 0, wx.ALL, 2)
        win_sizer.Add(hwin_sizer, 0, wx.ALL, 2)

        left_head_sizer.Add(loc_sizer, 0, wx.ALL, 4)
        left_head_sizer.Add(price_sizer, 0, wx.ALL|wx.GROW, 4)
        middle_head_sizer.Add(sol_sizer, 0, wx.ALL, 4)
        middle_head_sizer.Add(win_sizer, 0, wx.ALL, 4)

        head_sizer.Add(left_head_sizer, 0, wx.ALL, 2)
        head_sizer.Add(middle_head_sizer, 0, wx.ALL, 2)

        vbox.Add(head_sizer, 0, wx.ALL, 2)
        vbox.Add(canvas_sizer, 0, wx.ALL|wx.GROW)

        self.on_location_picked(None)
        self.SetSizer(vbox)

    # Simulate when button is clicked
    def on_simulate_clicked(self, event):
        try:
            turbine = Windturbine(self.wt_type_choice.GetString(self.wt_type_choice.GetCurrentSelection()))
            self.simulator = Simulator(self.location_obj, self.year_choice.GetString(self.year_choice.GetCurrentSelection()), 
                              turbine, latitude=self.latitude, longitude=self.longitude)
            self.cost_calculator = CostCalculator(self.sp_price, self.st_price, self.demand_input, 0, self.wt_price, 0, True, windturbine=turbine)
        except:
            wx.MessageBox('Please make sure you enter\na location, a year and a windturbine type', 'Input error', wx.OK)
            return

        self.solar_power, self.solar_energy = self.simulator.calc_solar(Az=[self.sp_or_1, self.sp_or_2, self.sp_or_3, self.sp_or_4], 
                                                                   Inc=[self.sp_ang_1, self.sp_ang_2, self.sp_ang_3, self.sp_ang_4], 
                                                                   sp_area=[self.sp_area_1, self.sp_area_2, self.sp_area_3, self.sp_area_4], sp_eff=self.sp_eff)
        self.wind_power, self.wind_energy = self.simulator.calc_wind([self.n_wt, self.wt_height])
        self.total_power = self.wind_power + self.solar_power
        self.total_energy = self.wind_energy + self.solar_energy

        self.demand_input = 6000
        self.demand = np.full(len(self.total_power), self.demand_input)

        
        stats = self.cost_calculator.get_stats(self.total_power, np.sum([self.sp_area_1, self.sp_area_2, self.sp_area_3, self.sp_area_4]), self.n_wt)


        self.power_surplus = stats['total_surplus']
        self.power_storage = stats['total_storage']
        self.power_shortage = stats['total_shortage']
        self.sol_cost = stats['solar_cost']
        self.win_cost = stats['wind_cost']
        self.stor_cost = stats['storage_cost']

        self.draw()

    # Cycle previous graph when button is clicked
    def on_prev_clicked(self, event):

        if self.plot_iter == 0:
            self.plot_iter = MAX_PLOTS
        else:
            self.plot_iter -= 1
        self.draw()

    # Cycle next graph when button is clicked
    def on_next_clicked(self, event):
        
        if self.plot_iter == MAX_PLOTS:
            self.plot_iter = 0
        else:
            self.plot_iter += 1
        self.draw()
    
    # Draw graph
    def draw(self):

        self.axes.clear() # Clear axes first

        # Check which graph is currently chosen and plot it
        if self.plot_iter == 0:
            self.axes.plot(np.mean(np.reshape(self.total_power[:8760], (365,24)), axis=1), color='green', alpha=0.5, label='Total')
            self.axes.plot(np.mean(np.reshape(self.demand[:8760], (365,24)), axis=1), color='red', alpha=0.5, label='Demand')
            self.axes.set_xlabel('Days')
            self.axes.set_ylabel('kW')
            self.axes.set_title('Power output for ' + self.location + ' ' + self.year_choice.GetString(self.year_choice.GetSelection()))
            self.axes.legend(loc='upper left')
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        if self.plot_iter == 1:
            self.axes.plot(np.mean(np.reshape(self.solar_power[:8760], (365,24)), axis=1), color='yellow', alpha=0.5, label='Solar')
            self.axes.plot(np.mean(np.reshape(self.wind_power[:8760], (365,24)), axis=1), color='blue', alpha=0.5, label='Wind')
            self.axes.plot(np.mean(np.reshape(self.demand[:8760], (365,24)), axis=1), color='red', alpha=0.5, label='Demand')
            self.axes.set_xlabel('Days')
            self.axes.set_ylabel('kW')
            self.axes.set_title('Split power output for ' + self.location + ' ' + self.year_choice.GetString(self.year_choice.GetSelection()))
            self.axes.legend(loc='upper left')
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        if self.plot_iter == 2:
            labels = 'Solar', 'Wind', 'Storage'
            sizes =  self.solar_energy[-1], self.wind_energy[-1], self.power_storage
            self.axes.pie(sizes, labels=labels, autopct='%1.1f%%')
            self.axes.set_title('Ratio\'s of power sources ' + self.location + ' ' + self.year_choice.GetString(self.year_choice.GetSelection()))
            self.axes.axis('equal')
            self.axes.set_frame_on(False)
        if self.plot_iter == 3:
            self.axes.plot(self.total_energy, color='green', alpha=0.5, label ='Total ')
            self.axes.plot(self.wind_energy, color='blue', alpha=0.5, label='Wind ')
            self.axes.plot(self.solar_energy, color='yellow', alpha=0.5, label='Solar ')
            self.axes.plot(np.cumsum(self.demand), color='red', alpha=0.5, label='Demand')
            self.axes.set_xlabel('Hours')
            self.axes.set_ylabel('kWh')
            self.axes.set_title('Split energy for ' + self.location + ' ' + self.year_choice.GetString(self.year_choice.GetSelection()))
            self.axes.legend(loc='upper left')
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        if self.plot_iter == 4:
            power =  self.total_power - self.demand_input
            for x in range(2) :
                if x == 0 :
                    batterycharge = [self.power_storage]
                else:
                    batterycharge = [batterycharge[-1]]
                Powershortage = []
                for I in power :
                    batterycharge.append(batterycharge[-1] + I)
                    if self.power_storage < batterycharge[-1]: 
                        batterycharge[-1] = self.power_storage
                    elif(0 > batterycharge[-1]) :
                        batterycharge[-1] = 0
                        Powershortage.append(len(batterycharge)-1)
            self.axes.plot(batterycharge, color='green', alpha=0.5, label='Storage')
            if len(Powershortage) == 0:
                self.axes.scatter(np.zeros(len(Powershortage)), Powershortage, color='red')
            self.axes.set_xlabel('Hours')
            self.axes.set_ylabel('kW')
            self.axes.set_title('Power from storage ' + self.location + ' ' + self.year_choice.GetString(self.year_choice.GetSelection()))
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        self.canvas.draw()

    # When a location is picked from dropdown, call update location information
    def on_location_picked(self, event):
        self.location = self.places.GetString(self.places.GetSelection())
        self.location_obj = Location(self.location)
        self.years = self.location_obj.get_years()
        self.years = np.flip(self.years)
        self.update_fields()

    # Update the location information
    def update_fields(self):
        self.year_choice.Clear()
        self.year_choice.AppendItems(self.years)

        self.lat_field.SetValue(f'{self.location_obj.latitude:.3f}')
        self.lon_field.SetValue(f'{self.location_obj.longitude:.3f}')
        self.ter_field.SetValue(f'{self.location_obj.terrain:.3f}')

    # When a field is changed, update the variables connected.
    # Add single field update in later versions with event-id linked to variable?    
    def on_fieldbox_changed(self, event):
        self.sp_area_1 = float(self.area_field1.GetValue()) if self.area_field1.GetValue() else 0
        self.sp_area_2 = float(self.area_field2.GetValue()) if self.area_field2.GetValue() else 0
        self.sp_area_3 = float(self.area_field3.GetValue()) if self.area_field3.GetValue() else 0
        self.sp_area_4 = float(self.area_field4.GetValue()) if self.area_field4.GetValue() else 0
        self.sp_or_1 = float(self.or_field1.GetValue()) if self.or_field1.GetValue() else 0
        self.sp_or_2 = float(self.or_field2.GetValue()) if self.or_field2.GetValue() else 0
        self.sp_or_3 = float(self.or_field3.GetValue()) if self.or_field3.GetValue() else 0
        self.sp_or_4 = float(self.or_field4.GetValue()) if self.or_field4.GetValue() else 0
        self.sp_ang_1 = float(self.angle_field1.GetValue()) if self.angle_field1.GetValue() else 0
        self.sp_ang_2 = float(self.angle_field2.GetValue()) if self.angle_field2.GetValue() else 0
        self.sp_ang_3 = float(self.angle_field3.GetValue()) if self.angle_field3.GetValue() else 0
        self.sp_ang_4 = float(self.angle_field4.GetValue()) if self.angle_field4.GetValue() else 0
        self.sp_eff = float(self.sp_eff_field.GetValue()) if self.sp_eff_field.GetValue() else 0
        self.latitude = float(self.lat_field.GetValue()) if self.lat_field.GetValue() else 0
        self.longitude = float(self.lon_field.GetValue()) if self.lon_field.GetValue() else 0
        self.terrain_factor = float(self.ter_field.GetValue()) if self.ter_field.GetValue() else 0
        self.wt_height = float(self.wth_field.GetValue()) if self.wth_field.GetValue() else 0
        self.n_wt = float(self.nwt_field.GetValue()) if self.nwt_field.GetValue() else 0
        self.sp_price = float(self.sp_price_field.GetValue()) if self.sp_price_field.GetValue() else 0
        self.wt_price = float(self.wt_price_field.GetValue()) if self.wt_price_field.GetValue() else 0
        self.st_price = float(self.st_price_field.GetValue()) if self.st_price_field.GetValue() else 0

    # Open file dialog when save button is clicked.
    def on_save_button_clicked(self, event):
        
        windfeatures = [int(self.n_wt), int(self.wt_height)]
        solarfeatures = [float(self.sp_area_1), float(self.sp_ang_1), float(self.sp_or_1), 
                         float(self.sp_area_2), float(self.sp_ang_2), float(self.sp_or_2),
                         float(self.sp_area_3), float(self.sp_ang_3), float(self.sp_or_3),
                         float(self.sp_area_4), float(self.sp_ang_4), float(self.sp_or_4)]

        params = {'location':self.location_obj, 'year_choice':self.year_choice.GetString(self.year_choice.GetCurrentSelection()),
                  'terrain_factor':self.terrain_factor, 'latitude':self.latitude,'longitude':self.longitude,
                  'windfeatures':windfeatures,'solarfeatures':solarfeatures,'sp_eff':self.sp_eff,
                  'wt_type':self.wt_type_choice.GetString(self.wt_type_choice.GetCurrentSelection()), 
                  'sp_price': self.sp_price, 'wt_price': self.wt_price, 'st_price':self.st_price,
                  'surp_price': 0, 'short_price': 0, 'demand' : 0}

        with wx.FileDialog(self, "Save simulation", defaultFile='Simulation_output', wildcard='excel files(*.xlsx)|*.xlsx',
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            path = fileDialog.GetPath()
            self.save_button.Disable()
            writer = FileWriter(self, path, **params)
            writer.start()

    # Let the user know file is done saving
    def on_savedone(self, evt):
        filename = evt.GetName()

        file_info = f'Simulation stored in {filename}'
        wx.MessageBox(file_info, 'Saving done', wx.OK)
        self.save_button.Enable()

class InputDialog(wx.Dialog):
    """
        Dialog for setting inputs in the training.
    """
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title='Inputs')

        # Populate locations list for dropdown
        self.locations = [i.lower().capitalize() for i in pd.read_csv('Data{}locations.csv'.format(os.sep),index_col=0, header=0).NAME.values]
        
        self.years = ['0000'] # placeholder for windows

        # Positional variables
        self.latitude = 0
        self.longitude = 0
        self.terrain_factor = 0

        # Configuration variables
        self.sp_eff = 0
        self.sp_area_min = 0
        self.sp_area_max = 0
        self.sp_ang_min = 0
        self.sp_ang_max = 0
        self.sp_or_min = 0
        self.sp_or_max = 0
        self.n_sp_configs = 0

        self.wtn_min = 0
        self.wtn_max = 0
        self.turbine_height = 0

        # REMOVE!
        self.demand = 0

        # GA variables
        self.generations = 0
        self.poolsize = 0
        self.m_rate = 0

        # Price variables 
        self.sp_price = 0
        self.wt_price = 0
        self.st_price = 0
        self.shortage_price = 0
        self.surplus_price = 400

        #Variable holding condition wether to trian by price or by output. True = train by price
        self.trainby = True

        #One large box to hold everything in the window
        vbox = wx.BoxSizer(wx.VERTICAL)

        #Staticboxes to seperate different groups
        sol_input_box = wx.StaticBox(self, -1, 'Solar panel inputs')
        win_input_box = wx.StaticBox(self, -1, 'Windturbine inputs')
        locbox = wx.StaticBox(self, -1, 'Location options')
        gabox = wx.StaticBox(self, -1, 'Genetic algorithm options')
        pricebox = wx.StaticBox(self, -1, 'Price options')

        #Vertical sizers
        sol_input_sizer = wx.StaticBoxSizer(sol_input_box, wx.VERTICAL)
        win_input_sizer = wx.StaticBoxSizer(win_input_box, wx.VERTICAL)
        loc_sizer = wx.StaticBoxSizer(locbox, wx.VERTICAL)
        ga_sizer = wx.StaticBoxSizer(gabox, wx.VERTICAL)
        price_sizer = wx.StaticBoxSizer(pricebox, wx.VERTICAL)

        #Horizontal sizers
        hsol_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hwin_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hloc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hga_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hprice_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hbutton_sizer = wx.BoxSizer(wx.HORIZONTAL)
        left_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        right_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        check_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        check_txt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        #Flexgrids to group elements neatly
        loc_grid = wx.FlexGridSizer(2, 2, 10, 10)
        sol_input_grid = wx.FlexGridSizer(4, 4, 10, 10)
        win_input_grid = wx.FlexGridSizer(3, 4, 10, 10)
        self.price_grid = wx.FlexGridSizer(5, 2, 10, 10)
        power_grid = wx.FlexGridSizer(3, 2, 10,10)
        ga_grid = wx.FlexGridSizer(2, 4, 10, 10)

        #Choice dropdown for location and year
        self.places = wx.Choice(self, wx.ID_ANY, choices=self.locations)
        self.year_choice = wx.Choice(self, wx.ID_ANY, choices=self.years)

        #Text input for latitude and longitude
        self.lat_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.latitude}')
        self.lon_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.longitude}')

        #Labels for lat and lon
        lat_txt = wx.StaticText(self, wx.ID_ANY, 'Latitude ')
        lon_txt = wx.StaticText(self, wx.ID_ANY, 'Longitude ')

        loc_grid.AddMany([(lat_txt, 0, wx.ALL, 2), (self.lat_field, 0, wx.ALL, 2),
                          (lon_txt, 0, wx.ALL, 2), (self.lon_field, 0, wx.ALL, 2)])

        hloc_sizer.AddMany([(self.places, 0, wx.ALL, 2),(self.year_choice, 0, wx.ALL, 2)])

        #Solar options
        sp_eff_txt = wx.StaticText(self, wx.ID_ANY, 'Panel efficiency ')
        self.sp_eff_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_eff}', name='sp_eff')
        sp_area_min_txt = wx.StaticText(self, wx.ID_ANY, 'Surface min ')
        self.sp_area_min_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_area_min}', name='sp_area_min')
        sp_area_max_txt = wx.StaticText(self, wx.ID_ANY, 'Surface max ')
        self.sp_area_max_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_area_max}', name='sp_area_max')
        sp_ang_min_txt = wx.StaticText(self, wx.ID_ANY, 'Angle min ')
        self.sp_ang_min_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_ang_min}', name='sp_ang_min')
        sp_ang_max_txt = wx.StaticText(self, wx.ID_ANY, 'Angle max ')
        self.sp_ang_max_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_ang_max}', name='sp_ang_max')
        sp_or_min_txt = wx.StaticText(self, wx.ID_ANY, 'Orientation min ')
        self.sp_or_min_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_or_min}', name='sp_or_min')
        sp_or_max_txt = wx.StaticText(self, wx.ID_ANY, 'Orientation max ')
        self.sp_or_max_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_or_max}', name='sp_or_max')

        #Number of configs.
        n_sp_configs_txt = wx.StaticText(self, wx.ID_ANY, 'Number of configs ')
        self.n_sp_configs_list = wx.Choice(self, wx.ID_ANY, choices=['4', '3', '2', '1'])

        sol_input_grid.AddMany([(sp_area_min_txt, 0, wx.ALL, 2), (self.sp_area_min_field, 0, wx.ALL, 2),
                                (sp_or_min_txt, 0, wx.ALL, 2), (self.sp_or_min_field, 0, wx.ALL, 2),
                                (sp_area_max_txt, 0, wx.ALL, 2), (self.sp_area_max_field, 0, wx.ALL, 2),
                                (sp_or_max_txt, 0, wx.ALL, 2), (self.sp_or_max_field, 0, wx.ALL, 2),
                                (sp_ang_min_txt, 0, wx.ALL, 2), (self.sp_ang_min_field, 0, wx.ALL, 2),
                                (sp_eff_txt, 0, wx.ALL, 2), (self.sp_eff_field, 0, wx.ALL, 2),
                                (sp_ang_max_txt, 0, wx.ALL, 2), (self.sp_ang_max_field, 0, wx.ALL, 2),
                                (n_sp_configs_txt, 0, wx.ALL, 2), (self.n_sp_configs_list, 0, wx.ALL, 2)])
        
        #Windturbine options
        wtn_min_txt = wx.StaticText(self, wx.ID_ANY, 'Minimum turbines ')
        self.wtn_min_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.wtn_min}', name='wtn_min')
        wtn_max_txt = wx.StaticText(self, wx.ID_ANY, 'Maximum turbines ')
        self.wtn_max_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.wtn_max}', name='wtn_max')
        turbine_height_txt = wx.StaticText(self, wx.ID_ANY, 'Turbine height ')
        self.turbine_height_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.turbine_height}', name='turbine_height')
        ter_txt = wx.StaticText(self, wx.ID_ANY, 'Terrain factor ')
        self.ter_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.terrain_factor}', name='terrain_factor')
        wt_type_txt = wx.StaticText(self, wx.ID_ANY, 'Type: ')
        self.wt_type_choice= wx.Choice(self, wx.ID_ANY, choices=[os.path.splitext(n)[0] for n in os.listdir(WT_PATH) if '.csv' in n])

        win_input_grid.AddMany([(wtn_min_txt, 0, wx.ALL, 2), (self.wtn_min_field, 0, wx.ALL, 2),
                                (wtn_max_txt, 0, wx.ALL, 2), (self.wtn_max_field, 0, wx.ALL, 2),
                                (turbine_height_txt, 0, wx.ALL, 2), (self.turbine_height_field, 0, wx.ALL, 2),
                                (ter_txt, 0, wx.ALL, 2), (self.ter_field, 0, wx.ALL, 2),
                                (wt_type_txt, 0, wx.ALL, 2), (self.wt_type_choice, 0, wx.ALL, 2)])

        #Genetic algorithm options
        demand_txt = wx.StaticText(self, wx.ID_ANY, 'Demand ')
        self.demand_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.demand}', name='demand')
        generations_txt = wx.StaticText(self, wx.ID_ANY, 'Generations ')
        self.generations_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.generations}', name='generations')
        poolsize_txt = wx.StaticText(self, wx.ID_ANY, 'Poolsize ')
        self.poolsize_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.poolsize}', name='pool_size')
        m_rate_txt = wx.StaticText(self, wx.ID_ANY, 'Mutation rate ')
        self.m_rate_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.m_rate}', name='mutation_rate')

        ga_grid.AddMany([(demand_txt, 0, wx.ALL, 2), (self.demand_field, 0, wx.ALL, 2), (m_rate_txt, 0, wx.ALL, 2),
                         (self.m_rate_field, 0, wx.ALL, 2), (generations_txt, 0, wx.ALL, 2), (self.generations_field, 0, wx.ALL, 2),
                         (poolsize_txt, 0, wx.ALL, 2), (self.poolsize_field, 0, wx.ALL, 2)])

        #Price options. Trainby is to input wether algoritm trains by power output or price of configuration
        trainby_txt = wx.StaticText(self, wx.ID_ANY, 'Train by: ')
        self.power_check = wx.RadioButton(self, wx.ID_ANY, 'Power')
        self.price_check = wx.RadioButton(self, wx.ID_ANY, 'Price')

        self.sp_price_txt = wx.StaticText(self, wx.ID_ANY, 'Solar panel (€/m²) ')
        self.sp_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.sp_price}', name='solar_panel_price')
        self.wt_price_txt = wx.StaticText(self, wx.ID_ANY, 'Wind turbine (€/kWh) ')
        self.wt_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.wt_price}', name='wind_turbine_price')
        self.st_price_txt = wx.StaticText(self, wx.ID_ANY, 'Storage (€/kWh)')
        self.st_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.st_price}', name='storage_price')
        self.short_price_txt = wx.StaticText(self, wx.ID_ANY, 'Shortage (€/kWh) ')
        self.short_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.shortage_price}', name='shortage_price')
        self.surplus_price_txt = wx.StaticText(self, wx.ID_ANY, 'Surplus price (€/kWh) ')
        self.surplus_price_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.surplus_price}', name='surplus_price')

        self.price_grid.AddMany([(self.sp_price_txt, 0, wx.ALL, 2), (self.sp_price_field), 
                            (self.wt_price_txt, 0, wx.ALL, 2), (self.wt_price_field, 0, wx.ALL, 2),
                            (self.surplus_price_txt, 0, wx.ALL, 2),(self.surplus_price_field, 0, wx.ALL, 2),
                            (self.st_price_txt, 0, wx.ALL, 2), (self.st_price_field, 0, wx.ALL, 2), 
                            (self.short_price_txt, 0, wx.ALL, 2), (self.short_price_field, 0 , wx.ALL, 2)])

        #Different buttons for stuff
        self.save_button = wx.Button(self, label='Save')
        self.cancel_button = wx.Button(self, label='Cancel')
        self.load_default_button = wx.Button(self, label='Load default', name='load_default')
        self.save_default_button = wx.Button(self, label='Save as default', name='save_default')

        left_button_sizer.AddMany([(self.save_default_button, 0, wx.ALL, 4), (self.load_default_button, 0, wx.ALL, 4)])
        right_button_sizer.AddMany([(self.cancel_button, 0, wx.ALL, 4), (self.save_button, 0, wx.ALL, 4)])
        
        hbutton_sizer.AddMany([(left_button_sizer, 0, wx.RIGHT, 35), (right_button_sizer, 0, wx.LEFT, 35)])

        #Binding certain events to functions
        self.places.Bind(wx.EVT_CHOICE, self.on_location_picked)
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_clicked)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel_clicked)
        self.load_default_button.Bind(wx.EVT_BUTTON, self.on_default_clicked)
        self.save_default_button.Bind(wx.EVT_BUTTON, self.on_save_default_clicked)
        self.power_check.Bind(wx.EVT_RADIOBUTTON, self.on_check_clicked)
        self.price_check.Bind(wx.EVT_RADIOBUTTON, self.on_check_clicked)

        #Binds for information popups
        self.wtn_min_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.wtn_max_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.turbine_height_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.ter_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.demand_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.generations_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.poolsize_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.m_rate_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.sp_price_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.wt_price_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.st_price_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.short_price_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.surplus_price_field.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.load_default_button.Bind(wx.EVT_MOTION, self.on_mouse_over)
        self.save_default_button.Bind(wx.EVT_MOTION, self.on_mouse_over)

        #Layout of the window
        check_txt_sizer.Add(trainby_txt, 0, wx.ALL, 2)
        check_button_sizer.Add(self.power_check, 0, wx.ALL, 2)
        check_button_sizer.Add(self.price_check, 0, wx.ALL, 2)
        price_sizer.Add(check_txt_sizer, 0, wx.ALL|wx.CENTER, 2)
        price_sizer.Add(check_button_sizer, 0, wx.ALL|wx.CENTER, 2)

        hsol_input_sizer.Add(sol_input_grid, 0, wx.ALL, 2)
        hwin_input_sizer.Add(win_input_grid, 0, wx.ALL, 2)
        hprice_sizer.Add(self.price_grid, 0, wx.ALL, 2)
        hga_sizer.Add(ga_grid, 0, wx.ALL, 2)

        loc_sizer.Add(hloc_sizer, 0, wx.ALL, 2)
        loc_sizer.Add(loc_grid, 0, wx.ALL, 2)
        sol_input_sizer.Add(hsol_input_sizer, 0, wx.ALL,2)
        win_input_sizer.Add(hwin_input_sizer, 0, wx.ALL, 2)
        price_sizer.Add(hprice_sizer, 0, wx.ALL, 2)
        ga_sizer.Add(hga_sizer, 0, wx.ALL, 2)

        head_sizer = wx.BoxSizer(wx.HORIZONTAL)
        head_sizer.Add(loc_sizer,0, wx.ALL, 2)
        head_sizer.Add(price_sizer, 0, wx.ALL, 2)

        vbox.Add(head_sizer, 0, wx.ALL, 2)
        vbox.Add(ga_sizer, 0, wx.ALL, 2)
        vbox.Add(win_input_sizer, 0, wx.ALL, 2)
        vbox.Add(sol_input_sizer, 0, wx.ALL, 2)
        vbox.Add(hbutton_sizer, 0, wx.ALL, 10)

        # Adapt screen to fit smaller displays
        self.EnableLayoutAdaptation(True)
        #Load defaults after window is made
        self.load_defaults()
        self.price_check.SetValue(True)
        self.on_check_clicked(None)

        #Set size and fit
        self.SetSizer(vbox)
        self.Fit()

    def on_mouse_over(self, event):
        #TODO: add tooltips for every field
        event_object = event.GetEventObject()
        event_object.SetToolTip(field_info(event_object.GetName()))

    def on_location_picked(self, event):
        """
            Creates location object when location is picked and 
            populates the year dropdown with available years for that location.
        """
        self.location = self.places.GetString(self.places.GetCurrentSelection())
        self.location_obj = Location(self.location)
        self.years = self.location_obj.get_years()
        self.years = np.flip(self.years)
        self.update_loc_settings()

    def on_save_clicked(self, event):
        """
            Gets the values from all fields and updates variables to corresponding fields. 
            Then the input dialog is closed
        """
        self.get_fields()
        self.Show(show=0)

    def on_cancel_clicked(self, event):
        """
            Reverts fields to the value of the variables and closes the input dialog.
        """
        self.update_fields()
        self.Show(show=0)

    def on_default_clicked(self, event):
        """
            Loads defaults into the fields
        """
        self.load_defaults()

    def on_save_default_clicked(self, event):
        """
            Saves values as default
        """
        self.save_default()

    def on_check_clicked(self, event):
        """
        Show/hide relevant options according to checkbox 
        """
        if(self.price_check.GetValue()):
            self.price_grid.Hide(self.surplus_price_txt)
            self.price_grid.Hide(self.surplus_price_field)
            self.price_grid.Show(self.sp_price_txt)
            self.price_grid.Show(self.sp_price_field)
            self.price_grid.Show(self.wt_price_txt)
            self.price_grid.Show(self.wt_price_field)
        else:
            self.price_grid.Show(self.surplus_price_txt)
            self.price_grid.Show(self.surplus_price_field)
            self.price_grid.Hide(self.sp_price_txt)
            self.price_grid.Hide(self.sp_price_field)
            self.price_grid.Hide(self.wt_price_txt)
            self.price_grid.Hide(self.wt_price_field)
            
        self.Layout()

    def update_loc_settings(self):
        """
            Updates the location settings. Gets called when a location is picked.
        """
        self.year_choice.Clear()
        self.year_choice.AppendItems(self.years)

        self.lat_field.SetValue(f'{self.location_obj.latitude:.3f}')
        self.lon_field.SetValue(f'{self.location_obj.longitude:.3f}')
        self.ter_field.SetValue(f'{self.location_obj.terrain:.3f}')

    def update_fields(self):
        """
            Updates all the fields to the value that is stored in the corresponding value.
            Gets called when configs are loaded or when the 'cancel' button is clicked
        """
        self.lat_field.SetValue(f'{self.latitude:.3f}')
        self.lon_field.SetValue(f'{self.longitude:.3f}')

        self.sp_eff_field.SetValue(f'{self.sp_eff}')
        self.sp_area_min_field.SetValue(f'{self.sp_area_min}')
        self.sp_area_max_field.SetValue(f'{self.sp_area_max}')
        self.sp_ang_min_field.SetValue(f'{self.sp_ang_min}')
        self.sp_ang_max_field.SetValue(f'{self.sp_ang_max}')
        self.sp_or_min_field.SetValue(f'{self.sp_or_min}')
        self.sp_or_max_field.SetValue(f'{self.sp_or_max}')

        self.wtn_min_field.SetValue(f'{self.wtn_min}')
        self.wtn_max_field.SetValue(f'{self.wtn_max}')
        self.turbine_height_field.SetValue(f'{self.turbine_height}')
        self.ter_field.SetValue(f'{self.terrain_factor:.3f}')

        self.demand_field.SetValue(f'{self.demand}')

        self.generations_field.SetValue(f'{self.generations}')
        self.poolsize_field.SetValue(f'{self.poolsize}')
        self.m_rate_field.SetValue(f'{self.m_rate}')

        self.sp_price_field.SetValue(f'{self.sp_price}')
        self.wt_price_field.SetValue(f'{self.wt_price}')
        self.st_price_field.SetValue(f'{self.st_price}')
        self.short_price_field.SetValue(f'{self.shortage_price}')
        self.surplus_price_field.SetValue(f'{self.surplus_price}')

    def get_fields(self):
        """ 
            Updates variables with values that are in the fields.
            This gets called when the 'save' button is clicked.
        """
        self.year = self.year_choice.GetCurrentSelection()
        self.latitude = float(self.lat_field.GetValue())
        self.longitude = float(self.lon_field.GetValue())
        self.terrain_factor = float(self.ter_field.GetValue())

        self.sp_eff = int(self.sp_eff_field.GetValue())
        self.sp_area_min = int(self.sp_area_min_field.GetValue())
        self.sp_area_max = int(self.sp_area_max_field.GetValue())
        self.sp_ang_min = int(self.sp_ang_min_field.GetValue())
        self.sp_ang_max = int(self.sp_ang_max_field.GetValue())
        self.sp_or_min = int(self.sp_or_min_field.GetValue())
        self.sp_or_max = int(self.sp_or_max_field.GetValue())
        self.n_sp_configs = int(self.n_sp_configs_list.GetCurrentSelection())

        self.wtn_min = int(self.wtn_min_field.GetValue())
        self.wtn_max = int(self.wtn_max_field.GetValue())
        self.turbine_height = int(self.turbine_height_field.GetValue())

        self.demand = int(self.demand_field.GetValue())

        self.generations = int(self.generations_field.GetValue())
        self.poolsize = int(self.poolsize_field.GetValue())
        self.m_rate = int(self.m_rate_field.GetValue())

        self.sp_price = int(self.sp_price_field.GetValue())
        self.wt_price = int(self.wt_price_field.GetValue())
        self.st_price = int(self.st_price_field.GetValue())
        self.shortage_price = int(self.short_price_field.GetValue())
        self.surplus_price = int(self.surplus_price_field.GetValue())
        self.trainby = self.price_check.GetValue()

    def load_defaults(self):
        """ 
            Load defaults from file and update the fields. 
        """
        defaults = pd.read_csv(f"config{os.sep}defaults{os.sep}train_defaults.csv", header=0)

        self.places.SetSelection(self.places.FindString(defaults.location_choice.values[0]))
        self.on_location_picked(None)
        self.year_choice.SetSelection(self.year_choice.FindString(f"{defaults.year_choice.values[0]}"))
        self.n_sp_configs_list.SetSelection(self.n_sp_configs_list.FindString(f"{(defaults.n_sp_configs_choice.values[0])}"))
        self.wt_type_choice.SetSelection(self.wt_type_choice.FindString(defaults.turbine_type.values[0]))

        self.location = defaults.location.values[0]
        self.year = defaults.year.values[0]
        self.latitude = defaults.latitude.values[0]
        self.longitude = defaults.longitude.values[0]

        self.sp_eff = defaults.sp_eff.values[0]
        self.sp_area_min = defaults.sp_area_min.values[0]
        self.sp_area_max = defaults.sp_area_max.values[0]
        self.sp_ang_min = defaults.sp_ang_min.values[0]
        self.sp_ang_max = defaults.sp_ang_max.values[0]
        self.sp_or_min = defaults.sp_or_min.values[0]
        self.sp_or_max = defaults.sp_or_max.values[0]
        self.n_sp_configs = defaults.n_sp_configs.values[0]

        self.wtn_min = defaults.wtn_min.values[0]
        self.wtn_max = defaults.wtn_max.values[0]
        self.turbine_height = defaults.turbine_height.values[0]
        self.terrain_factor = defaults.terrain_factor.values[0]

        self.demand = defaults.demand.values[0]

        self.generations = defaults.generations.values[0]
        self.poolsize = defaults.poolsize.values[0]
        self.m_rate = defaults.m_rate.values[0]

        self.sp_price = defaults.sp_price.values[0]
        self.wt_price = defaults.wt_price.values[0]
        self.st_price = defaults.st_price.values[0]
        self.shortage_price = defaults.shortage_price.values[0]
        self.n_sp_configs = defaults.n_sp_configs.values[0]

        self.update_fields()

    def save_default(self):
        """
            Stores inputs in a csv file to load as default later.
        """
        self.get_fields()
        defaults = {'location':self.location,'year': self.year,
                    'latitude':self.latitude,'longitude':self.longitude,
                    'sp_eff': self.sp_eff, 'sp_area_min': self.sp_area_min, 
                    'sp_area_max': self.sp_area_max, 'sp_ang_min': self.sp_ang_min, 
                    'sp_ang_max': self.sp_ang_max, 'sp_or_min': self.sp_or_min, 
                    'sp_or_max': self.sp_or_max, 'n_sp_configs': self.n_sp_configs,
                    'turbine_height': self.turbine_height, 'terrain_factor':self.terrain_factor,
                    'turbine_type': self.wt_type_choice.GetString(self.wt_type_choice.GetCurrentSelection()),
                    'wtn_min': self.wtn_min, 'wtn_max': self.wtn_max,
                    'demand': self.demand, 'generations': self.generations, 
                    'poolsize': self.poolsize, 'm_rate': self.m_rate, 
                    'sp_price': self.sp_price, 'wt_price': self.wt_price, 
                    'st_price': self.st_price, 'shortage_price': self.shortage_price, 'surplus_price': self.surplus_price,
                    'n_config_':self.n_sp_configs,'year_choice':self.year_choice.GetString(self.year_choice.GetCurrentSelection()),
                    'location_choice':self.places.GetString(self.places.GetCurrentSelection()),'n_sp_configs_choice':self.n_sp_configs_list.GetString(self.n_sp_configs_list.GetCurrentSelection())}
        pd.DataFrame([defaults]).to_csv('config{sep}defaults{sep}train_defaults.csv'.format(sep=os.sep))

        file_info = 'Current inputs saved as default.'
        wx.MessageBox(file_info, 'Defaults saved', wx.OK)

class TrainTab(wx.Panel):
    def __init__(self, parent):
        """
            Tab for training the genetic algorithm. 
            Also displays the graphs for corresponding congfiguration.
        """
        wx.Panel.__init__(self, parent)

        # Populate list with locations. 
        self.locations = [i.lower().capitalize() for i in pd.read_csv('Data/locations.csv',index_col=0,header=0).NAME.values]
        self.years= ['0000'] # Placeholder again

        # Dialog for setting all the inputs
        self.dialog = InputDialog(self)

        # Variables for outputs
        self.sp_area_1 = 0
        self.sp_area_2 = 0
        self.sp_area_3 = 0
        self.sp_area_4 = 0
        self.sp_or_1 = 0
        self.sp_or_2 = 0
        self.sp_or_3 = 0
        self.sp_or_4 = 0
        self.sp_ang_1 = 0
        self.sp_ang_2 = 0
        self.sp_ang_3 = 0
        self.sp_ang_4 = 0

        self.n_wt = 0
        self.wt_height = 0

        self.solar_power = None
        self.wind_power = None
        self.total_power = None

        self.solar_energy = None
        self.wind_energy = None
        self.total_energy = None

        self.demand = None

        self.power_surplus = 0
        self.power_shortage = 0
        self.power_storage = 0

        self.sol_cost = 0
        self.win_cost = 0
        self.stor_cost = 0
        self.tot_cost = 0

        self.n_sp_configs = 4

        self.costcalculator = None
        self.simulator = None

        self.plot_iter = 0

        self.config = None
        self.train_worker = None

        # Bind events to corresponding functions
        self.Bind(EVT_GENDONE, self.on_gendone)
        self.Bind(EVT_TRAINDONE, self.on_training_done)
        self.Bind(EVT_SAVEDONE, self.on_savedone)
        
        vbox = wx.BoxSizer(wx.VERTICAL)

        sol_output_box = wx.StaticBox(self, -1, 'Solar panel outputs')
        win_output_box = wx.StaticBox(self, -1, 'Windturbine outputs')
        stat_box = wx.StaticBox(self, -1, 'Power statistics')
        cost_box = wx.StaticBox(self, -1, 'Cost statistics')
        canvas_box = wx.StaticBox(self, -1, 'Graph')

        sol_output_sizer = wx.StaticBoxSizer(sol_output_box, wx.VERTICAL)
        win_output_sizer = wx.StaticBoxSizer(win_output_box, wx.VERTICAL)
        stat_sizer = wx.StaticBoxSizer(stat_box, wx.VERTICAL)
        canvas_sizer = wx.StaticBoxSizer(canvas_box, wx.VERTICAL)
        cost_sizer = wx.StaticBoxSizer(cost_box, wx.VERTICAL)

        input_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filename_sizer = wx.BoxSizer(wx.HORIZONTAL)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_left_sizer = wx.BoxSizer(wx.VERTICAL)
        top_middle_sizer = wx.BoxSizer(wx.VERTICAL)
        top_right_sizer = wx.BoxSizer(wx.VERTICAL)

        sol_output_grid = wx.FlexGridSizer(3, 5, 10, 10)
        win_output_grid = wx.FlexGridSizer(2, 2, 10, 10)
        stat_grid = wx.FlexGridSizer(3, 2, 10, 10)
        cost_grid = wx.FlexGridSizer(4, 2, 10, 10)

        self.input_button = wx.Button(self, wx.ID_ANY, label='Set inputs')
        self.start_button = wx.Button(self, label='Start training')
        self.stop_button = wx.Button(self, label='Stop training')
        self.save_button = wx.Button(self, label='Save configuration')
        self.nextgraph_button = wx.Button(self, label='>')
        self.previousgraph_button = wx.Button(self, label='<')

        self.start_button.Bind(wx.EVT_BUTTON, self.on_start_clicked)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop_clicked)
        self.input_button.Bind(wx.EVT_BUTTON, self.on_inputbutton_clicked)
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_clicked)
        self.nextgraph_button.Bind(wx.EVT_BUTTON, self.on_next_clicked)
        self.previousgraph_button.Bind(wx.EVT_BUTTON, self.on_prev_clicked)

        progress_txt = wx.StaticText(self, wx.ID_ANY, 'Progress: ')
        self.progress = wx.Gauge(self, size=(400,20))
        
        sp_area_txt = wx.StaticText(self, wx.ID_ANY, 'Surfaces ')
        self.sp_area_1_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_area_1}')
        self.sp_area_2_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_area_2}')
        self.sp_area_3_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_area_3}')
        self.sp_area_4_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_area_4}')

        sp_ang_txt = wx.StaticText(self, wx.ID_ANY, 'Angles ')
        self.sp_ang_1_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_ang_1}')
        self.sp_ang_2_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_ang_2}')
        self.sp_ang_3_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_ang_3}')
        self.sp_ang_4_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_ang_4}')

        sp_or_txt = wx.StaticText(self, wx.ID_ANY, 'Orientations ')
        self.sp_or_1_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_or_1}')
        self.sp_or_2_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_or_2}')
        self.sp_or_3_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_or_3}')
        self.sp_or_4_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sp_or_4}')

        sol_output_grid.AddMany([(sp_area_txt, 0, wx.ALL, 2), (self.sp_area_1_field, 0, wx.ALL, 2), (self.sp_area_2_field, 0, wx.ALL, 2), 
                                 (self.sp_area_3_field, 0, wx.ALL, 2), (self.sp_area_4_field, 0, wx.ALL, 2),
                                 (sp_ang_txt, 0, wx.ALL, 2), (self.sp_ang_1_field, 0, wx.ALL, 2), (self.sp_ang_2_field, 0, wx.ALL, 2), 
                                 (self.sp_ang_3_field, 0, wx.ALL, 2), (self.sp_ang_4_field, 0, wx.ALL, 2),
                                 (sp_or_txt, 0, wx.ALL, 2), (self.sp_or_1_field, 0, wx.ALL, 2), (self.sp_or_2_field, 0, wx.ALL, 2), 
                                 (self.sp_or_3_field, 0, wx.ALL, 2), (self.sp_or_4_field, 0, wx.ALL, 2)])

        wt_n_txt = wx.StaticText(self, wx.ID_ANY, 'Turbines ')
        self.wtn_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.n_wt}')
        wt_h_txt = wx.StaticText(self, wx.ID_ANY, 'Turbine height (m) ')
        self.wth_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.wt_height}')

        storage_txt = wx.StaticText(self, wx.ID_ANY, 'Power storage (kWh) ')
        self.storage_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.power_storage}')
        surplus_txt = wx.StaticText(self, wx.ID_ANY, 'Power surplus (kWh) ')
        self.surplus_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.power_surplus}')
        shortage_txt = wx.StaticText(self, wx.ID_ANY, 'Power shortage (kWh) ')
        self.shortage_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.power_shortage}')

        sol_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Solar cost (k€) ')
        self.sol_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.sol_cost}')
        win_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Wind cost (k€) ')
        self.win_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.win_cost}')
        stor_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Storage cost (k€) ')
        self.stor_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=f'{self.stor_cost}')
        tot_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Total cost (k€) ')
        self.tot_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value =f'{self.tot_cost}')

        # Plot setup
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)

        graph_button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # The (0, 0, 1) is the spacer to make the save button align to the right
        graph_button_sizer.AddMany([(self.previousgraph_button, 0, wx.ALL, 2), (self.nextgraph_button, 0, wx.ALL, 2),
                                    (0, 0, 1), (self.save_button, 0, wx.ALL, 2)])
        canvas_sizer.Add(graph_button_sizer, 0, wx.ALL|wx.EXPAND, 2)
        canvas_sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)

        input_button_sizer.AddMany([(self.input_button, 0, wx.RIGHT, 100), (self.stop_button, 0, wx.RIGHT, 4), 
                                    (self.start_button, 0, wx.RIGHT, 4), (progress_txt, 0, wx.ALL, 2), (self.progress, 1, wx.ALL, 2)])

        win_output_grid.AddMany([(wt_n_txt, 0, wx.ALL, 2), (self.wtn_field, 0, wx.ALL, 2),
                                 (wt_h_txt, 0, wx.ALL, 2), (self.wth_field, 0, wx.ALL, 2)])

        stat_grid.AddMany([(storage_txt, 0, wx.ALL, 2), (self.storage_field, 0, wx.ALL, 2), 
                           (surplus_txt, 0 , wx.ALL, 2), (self.surplus_field, 0, wx.ALL, 2),
                           (shortage_txt, 0, wx.ALL, 2),(self.shortage_field, 0, wx.ALL, 2)])

        cost_grid.AddMany([(sol_cost_txt, 0, wx.ALL, 2), (self.sol_cost_field, 0, wx.ALL, 2),
                           (win_cost_txt, 0, wx.ALL, 2), (self.win_cost_field, 0, wx.ALL, 2),
                           (stor_cost_txt, 0, wx.ALL, 2), (self.stor_cost_field, 0, wx.ALL, 2),
                           (tot_cost_txt, 0, wx.ALL, 2), (self.tot_cost_field, 0, wx.ALL, 2)])

        sol_output_sizer.Add(sol_output_grid, 0, wx.ALL, 2)
        win_output_sizer.Add(win_output_grid, 0, wx.ALL, 2)
        stat_sizer.Add(stat_grid, 0, wx.ALL, 2)
        cost_sizer.Add(cost_grid, 0, wx.ALL, 2)

        top_left_sizer.AddMany([(sol_output_sizer, 0, wx.ALL, 2), (win_output_sizer, 0, wx.ALL, 2)])
        top_middle_sizer.Add(cost_sizer, 0, wx.ALL, 2)
        top_right_sizer.Add(stat_sizer, 0, wx.ALL, 2)

        top_sizer.AddMany([(top_left_sizer, 0, wx.ALL, 0),
                           (top_middle_sizer, 0, wx.ALL, 0),
                           (top_right_sizer, 0, wx.ALL, 0)])

        vbox.Add(input_button_sizer, 0, wx.ALL, 4)
        vbox.Add(top_sizer, 0, wx.ALL, 2)

        vbox.Add(canvas_sizer, 0, wx.ALL|wx.GROW, 2)

        self.SetSizer(vbox)
        self.Fit()

    # Cycle previous graph when button is clicked
    def on_prev_clicked(self, event):

        if self.plot_iter == 0:
            self.plot_iter = MAX_PLOTS
        else:
            self.plot_iter -= 1
        self.draw()

    # Cycle next graph when button is clicked
    def on_next_clicked(self, event):
        
        if self.plot_iter == MAX_PLOTS:
            self.plot_iter = 0
        else:
            self.plot_iter += 1
        self.draw()

    # Update the output field to the values stored in variables
    def update_outputs(self):

        self.sp_area_1_field.SetValue(f'{self.sp_area_1}')
        self.sp_area_2_field.SetValue(f'{self.sp_area_2}')
        self.sp_area_3_field.SetValue(f'{self.sp_area_3}')
        self.sp_area_4_field.SetValue(f'{self.sp_area_4}')

        self.sp_ang_1_field.SetValue(f'{self.sp_ang_1}')
        self.sp_ang_2_field.SetValue(f'{self.sp_ang_2}')
        self.sp_ang_3_field.SetValue(f'{self.sp_ang_3}')
        self.sp_ang_4_field.SetValue(f'{self.sp_ang_4}')

        self.sp_or_1_field.SetValue(f'{self.sp_or_1}')
        self.sp_or_2_field.SetValue(f'{self.sp_or_2}')
        self.sp_or_3_field.SetValue(f'{self.sp_or_3}')
        self.sp_or_4_field.SetValue(f'{self.sp_or_4}')

        self.wtn_field.SetValue(f'{self.n_wt}')
        self.wth_field.SetValue(f'{self.wt_height}')

        self.storage_field.SetValue(f'{int(self.power_storage):,}')
        self.surplus_field.SetValue(f'{int(self.power_surplus):,}')
        self.shortage_field.SetValue(f'{int(self.power_shortage):,}')

        self.sol_cost_field.SetValue(f'{(int(self.sol_cost/1000)):,}')
        self.win_cost_field.SetValue(f'{(int(self.win_cost/1000)):,}')
        self.stor_cost_field.SetValue(f'{(int(self.stor_cost/1000)):,}')
        self.tot_cost_field.SetValue(f'{(int(self.tot_cost/1000)):,}')

    # Open the input dialog when the input button is clicked
    def on_inputbutton_clicked(self, event):
        self.dialog.Show(show=1)

    # Start the trainworker when the start button is clicked
    def on_start_clicked(self, event):

        # Disable the start button to prevent double clicks
        self.start_button.Disable()

        self.progress.SetRange(self.dialog.generations)
        self.axes.clear()

        turbine = Windturbine(self.dialog.wt_type_choice.GetString(self.dialog.wt_type_choice.GetSelection()))
        self.simulator = Simulator(Location(self.dialog.location), self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()), 
                                            turbine, latitude=self.dialog.latitude, 
                                            longitude=self.dialog.longitude, terrain_factor=self.dialog.terrain_factor)
        self. costcalculator = CostCalculator(self.dialog.sp_price, self.dialog.st_price, 
                                                       self.dialog.demand, self.dialog.shortage_price, 
                                                       self.dialog.wt_price, self.dialog.surplus_price, 
                                                       self.dialog.trainby,turbine)

        parameters = {'generations':self.dialog.generations, 'group_size':self.dialog.poolsize, 
                  'n_configs':({0:4, 1:3, 2:2, 3:1}.get(self.dialog.n_sp_configs)), 
                  'surface_min':self.dialog.sp_area_min, 'surface_max':self.dialog.sp_area_max, 
                  'angle_min':self.dialog.sp_ang_min, 'angle_max':self.dialog.sp_ang_max, 
                  'orientation_min':self.dialog.sp_or_min, 'orientation_max':self.dialog.sp_or_max, 
                  'sp_eff':self.dialog.sp_eff, 'mutation_percentage':self.dialog.m_rate, 
                  'turbines_min':self.dialog.wtn_min, 'turbines_max':self.dialog.wtn_max, 
                  'turbine_height':self.dialog.turbine_height, 'turbine_type':self.dialog.wt_type_choice.GetString(self.dialog.wt_type_choice.GetSelection()), 
                  'solar_price':self.dialog.sp_price, 'storage_price':self.dialog.st_price, 'demand':self.dialog.demand, 
                  'shortage_price':self.dialog.shortage_price, 'turbine_price':self.dialog.wt_price, 
                  'surplus_price':self.dialog.surplus_price, 'train_by_price':self.dialog.trainby,
                  'location':self.dialog.location, 'year':self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()), 
                  'latitude':self.dialog.latitude, 'longitude':self.dialog.longitude, 'terrain_factor':self.dialog.terrain_factor
        }

        try:
            self.train_worker = TrainWorker(self, parameters)
            self.train_worker.start()
        except:
            wx.MessageBox('Please make sure you enter all inputs.\nIf problem persists contact developer.', 'Train error', wx.OK)
            self.start_button.Enable()

    # When stop is clicked stop the train worker and enable the start button
    def on_stop_clicked(self, event):
        self.train_worker.stop()
        self.progress.SetValue(0)
        self.start_button.Enable()

    # When generation done event is fired update the variables for outputs
    # and call the update function and draw function
    def on_gendone(self, event):
        self.progress.SetValue(event.data[1]+1)
        self.config = event.data[0].astype(int)
        solar_features = self.config[:-1]
        turbines = self.config[-1]

        surface_features = solar_features[0::3]
        angle_features = solar_features[1::3]
        orientation_features = solar_features[2::3]
        
        self.sp_area_1 = surface_features[0]
        self.sp_area_2 = 0 if len(surface_features) < 2 else surface_features[1]
        self.sp_area_3 = 0 if len(surface_features) < 3 else surface_features[2]
        self.sp_area_4 = 0 if len(surface_features) < 4 else surface_features[3]
        self.sp_or_1 = orientation_features[0]
        self.sp_or_2 = 0 if len(orientation_features) < 2 else orientation_features[1]
        self.sp_or_3 = 0 if len(orientation_features) < 3 else orientation_features[2]
        self.sp_or_4 = 0 if len(orientation_features) < 4 else orientation_features[3]
        self.sp_ang_1 = angle_features[0]
        self.sp_ang_2 = 0 if len(angle_features) < 2 else angle_features[1]
        self.sp_ang_3 = 0 if len(angle_features) < 3 else angle_features[2]
        self.sp_ang_4 = 0 if len(angle_features) < 4 else angle_features[3]
        self.n_wt = turbines
        self.wt_height = self.dialog.turbine_height

        self.solar_power, self.solar_energy = self.simulator.calc_solar(Az=orientation_features, 
                                                              Inc=angle_features, 
                                                              sp_area=surface_features, 
                                                              sp_eff=self.dialog.sp_eff)
        self.wind_power, self.wind_energy = self.simulator.calc_wind([turbines, self.wt_height])

        self.total_power = self.wind_power + self.solar_power
        self.total_energy = self.wind_energy + self.solar_energy

        self.demand = np.full(len(self.total_energy), self.dialog.demand)

        stats = self.costcalculator.get_stats(self.total_power, np.sum(surface_features), turbines)

        self.power_surplus = stats['total_surplus']
        self.power_storage = stats['total_storage']
        self.power_shortage = stats['total_shortage']
        self.sol_cost = int(stats['solar_cost'])
        self.win_cost = int(stats['wind_cost'])
        self.stor_cost = int(stats['storage_cost'])
        self.tot_cost = self.stor_cost + self.win_cost + self.sol_cost

        self.update_outputs()

        self.draw()

    # Draw the graph for the current outputs shown.
    def draw(self):

        # Clear axes first
        self.axes.clear()

        # Check which graph is selected and draw it.
        if self.plot_iter == 0:
            self.axes.plot(np.mean(np.reshape(self.total_power[:8760], (365,24)), axis=1), color='green', alpha=0.5, label='Total')
            self.axes.plot(np.mean(np.reshape(self.demand[:8760], (365,24)), axis=1), color='red', alpha=0.5, label='Demand')
            self.axes.set_xlabel('Days')
            self.axes.set_ylabel('kW')
            self.axes.set_title('Power output for ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()))
            self.axes.legend(loc='upper left')
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        if self.plot_iter == 1:
            self.axes.plot(np.mean(np.reshape(self.solar_power[:8760], (365,24)), axis=1), color='yellow', alpha=0.5, label='Solar')
            self.axes.plot(np.mean(np.reshape(self.wind_power[:8760], (365,24)), axis=1), color='blue', alpha=0.5, label='Wind')
            self.axes.plot(np.mean(np.reshape(self.demand[:8760], (365,24)), axis=1), color='red', alpha=0.5, label='Demand')
            self.axes.set_xlabel('Days')
            self.axes.set_ylabel('kW')
            self.axes.set_title('Split power output for ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()))
            self.axes.legend(loc='upper left')
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        if self.plot_iter == 2:
            labels = 'Solar', 'Wind', 'Storage'
            sizes =  self.solar_energy[-1], self.wind_energy[-1], self.power_storage
            self.axes.pie(sizes, labels=labels, autopct='%1.1f%%')
            self.axes.set_title('Ratio\'s of power sources ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()))
            self.axes.axis('equal')
            self.axes.set_frame_on(False)
        if self.plot_iter == 3:
            self.axes.plot(self.total_energy, color='green', alpha=0.5, label ='Total ')
            self.axes.plot(self.wind_energy, color='blue', alpha=0.5, label='Wind ')
            self.axes.plot(self.solar_energy, color='yellow', alpha=0.5, label='Solar ')
            self.axes.plot(np.cumsum(self.demand), color='red', alpha=0.5, label='Demand')
            self.axes.set_xlabel('Hours')
            self.axes.set_ylabel('kWh')
            self.axes.set_title('Split energy for  ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()))
            self.axes.legend(loc='upper left')
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        if self.plot_iter == 4:
            power =  self.total_power - 6000
            for x in range(2) :
                if x == 0 :
                    batterycharge = [self.power_storage]
                else:
                    batterycharge = [batterycharge[-1]]
                Powershortage = []
                for I in power :
                    batterycharge.append(batterycharge[-1] + I)
                    if self.power_storage < batterycharge[-1]: 
                        batterycharge[-1] = self.power_storage
                    elif(0 > batterycharge[-1]) :
                        batterycharge[-1] = 0
                        Powershortage.append(len(batterycharge)-1)
            self.axes.plot(batterycharge, color='green', alpha=0.5, label='Storage')
            if len(Powershortage) == 0:
                self.axes.scatter(np.zeros(len(Powershortage)), Powershortage, color='red')
            self.axes.set_xlabel('Hours')
            self.axes.set_ylabel('kW')
            self.axes.set_title('Power from storage ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection()))
            self.axes.set_frame_on(True)
            self.axes.axis('tight')
        self.canvas.draw()

    # Open the save dialog when the save button is clicked.
    def on_save_clicked(self, event):

        windfeatures = [int(self.n_wt), int(self.wt_height)]
        solarfeatures = [float(self.sp_area_1), float(self.sp_ang_1), float(self.sp_or_1), 
                         float(self.sp_area_2), float(self.sp_ang_2), float(self.sp_or_2),
                         float(self.sp_area_3), float(self.sp_ang_3), float(self.sp_or_3),
                         float(self.sp_area_4), float(self.sp_ang_4), float(self.sp_or_4)]
        price_params = [self.dialog.sp_price, self.dialog.wt_price, self.dialog.st_price]

        params = {'location':Location(self.dialog.location), 'year_choice':self.dialog.year_choice.GetString(self.dialog.year_choice.GetCurrentSelection()),
                  'terrain_factor':self.dialog.terrain_factor, 'latitude':self.dialog.latitude,
                  'longitude':self.dialog.longitude,
                  'windfeatures':windfeatures,'solarfeatures':solarfeatures,'sp_eff':self.dialog.sp_eff,
                  'sp_price': self.dialog.sp_price, 'wt_price':self.dialog.wt_price, 'st_price': self.dialog.st_price,
                  'wt_type':self.dialog.wt_type_choice.GetString(self.dialog.wt_type_choice.GetSelection()),
                  'short_price':self.dialog.shortage_price , 'surp_price':self.dialog.surplus_price,
                  'demand':self.dialog.demand}

        with wx.FileDialog(self, "Save trianing", defaultFile='Training_output', wildcard='excel files(*.xlsx)|*.xlsx',
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            path = fileDialog.GetPath()
            self.save_button.Disable()
            writer = FileWriter(self, path, **params)
            writer.start()

    # Let the user know the file was saved succesfully
    def on_savedone(self, evt):
        filename = evt.GetName()

        file_info = 'Training output stored in {}'.format(filename)
        wx.MessageBox(file_info, 'Saving done', wx.OK)
        
        self.save_button.Enable()

    # Let the user know when a training is done.
    def on_training_done(self, evt):
        
        file_info = 'Training done for ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection())
        wx.MessageBox(file_info, 'Training done', wx.OK)

        self.progress.SetValue(0)
        self.start_button.Enable()

class TurbineDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title='Turbine curve')

        self.windcurve = None
        self.powercurve = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)
        gridbox = wx.BoxSizer(wx.HORIZONTAL)
        optionbox = wx.BoxSizer(wx.HORIZONTAL)
        choicebox = wx.BoxSizer(wx.HORIZONTAL)

        self.save_button = wx.Button(self, wx.ID_ANY, label='Save ')
        self.name_field = wx.TextCtrl(self, wx.ID_ANY, value= '')
        self.turbine_choice = wx.Choice(self, wx.ID_ANY, choices=[os.path.splitext(n)[0] for n in os.listdir(WT_PATH) if '.csv' in n])
        
        self.turbine_choice.Bind(wx.EVT_CHOICE, self.on_turbine_selected)
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_turbine)

        self.wind_txt = wx.StaticText(self, wx.ID_ANY, 'Wind curve ')
        self.wind_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.windcurve}', size=(500,25))

        self.power_txt = wx.StaticText(self, wx.ID_ANY, 'Power curve ')
        self.power_field = wx.TextCtrl(self, wx.ID_ANY, value=f'{self.powercurve}', size=(500,25))

        grid.AddMany([(self.wind_txt, 0, wx.ALL, 2), (self.wind_field, 0 ,wx.ALL, 2),
                      (self.power_txt, 0, wx.ALL, 2), (self.power_field, 0, wx.ALL, 2)])

        choicebox.Add(self.turbine_choice, 0, wx.ALL, 2)
        gridbox.Add(grid, 0, wx.ALL, 2)
        optionbox.AddMany([(self.save_button, 0, wx.ALL, 2), (self.name_field, 0 , wx.ALL, 2)])
        
        sizer.AddMany([(choicebox, 0, wx.ALL, 2), (gridbox, 0, wx.ALL, 2), (optionbox, 0, wx.ALL, 2)])
        self.SetSizer(sizer)
        self.Fit()

    def load_turbine(self, ttype):
        turbine = pd.read_csv(f'config{os.sep}turbines{os.sep}{ttype}.csv', index_col=0)
        self.windcurve = turbine.wind.values.tolist()
        self.powercurve = turbine.power.values.tolist()
        self.power_field.SetValue(f'{self.powercurve}'.replace('[','').replace(']',''))
        self.wind_field.SetValue(f'{self.windcurve}'.replace('[','').replace(']',''))
        self.name_field.SetValue(ttype)

    def on_save_turbine(self, event):
        ttype = self.name_field.GetValue()
        path = f'config{os.sep}turbines{os.sep}{ttype}.csv'

        # check if the file already exists and warm user if so.
        if os.path.exists(path):
            with  wx.MessageDialog(self, 'This file already exists.\nIf you save under the same name file will be overwritten.\nContinue?', 'Warning', wx.YES_NO) as mesbox:
                if mesbox.ShowModal() == wx.ID_NO:
                    return
                self.save_turbine(path)
        else:
            self.save_turbine(path)
        wx.MessageBox('New turbine saved succesfully', 'Saved', wx.OK)

    def save_turbine(self, path):
        # convert strings to int lists
        windcurve = list(map(float,self.wind_field.GetValue().split(',')))
        powercurve = list(map(int,self.power_field.GetValue().split(',')))
        # create pandas dataframe and save it
        dataframe = pd.DataFrame()
        dataframe['power'] = powercurve
        dataframe['wind'] = windcurve
        dataframe.to_csv(path)


    def on_turbine_selected(self, event):
        ttype = self.turbine_choice.GetString(self.turbine_choice.GetCurrentSelection())
        self.load_turbine(ttype)


class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title='Simtool')

        # Notebook for multiple tabs
        nb = wx.Notebook(self)

        # Seperate tab objects for simulating and training
        tab1 = SimTab(nb)
        tab2 = TrainTab(nb)
        self.turbine_dialog= TurbineDialog(self)

        # Add the tabs to the botebook
        nb.AddPage(tab1, 'Simulation')
        nb.AddPage(tab2, 'Training')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(nb, 1, wx.ALL|wx.EXPAND, 2)

        # Dropdown menu for about etc.
        self.menu_bar  = wx.MenuBar() 
        
        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_ABOUT, '&About Simtool')
        
        self.edit_menu = wx.Menu()
        self.edit_menu.Append(wx.ID_EDIT, '&Windturbine editor')
        
        self.menu_bar.Append(self.edit_menu, '&Edit')
        self.menu_bar.Append(self.help_menu, '&Help')

        self.SetMenuBar(self.menu_bar)
        self.Bind(wx.EVT_MENU, self.on_about_request, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.on_turbine_editor, id=wx.ID_EDIT)

        self.SetSizer(sizer)
        self.Layout()
        self.Fit()

    # Small dialog showing about info when about is selected from dropdown.
    def on_about_request(self, id):
        info = 'For all information regarding Simtool visit\nwww.github.com/Jerscovad/Simulatietool'
        wx.MessageBox(info, 'About', wx.OK)

    # Windturbine editor for adding and editing windturbine curves.
    def on_turbine_editor(self, id):
        self.turbine_dialog.Show()

if __name__ == "__main__":
    app = wx.App()
    MainFrame().Show()
    app.MainLoop()