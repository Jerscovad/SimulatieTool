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
from calculate_cost import CostCalculator
from location import Location
import matplotlib
matplotlib.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

myEVT_SAVEDONE = wx.NewEventType()
EVT_SAVEDONE = wx.PyEventBinder(myEVT_SAVEDONE, 1)

myEVT_TRAINDONE = wx.NewEventType()
EVT_TRAINDONE = wx.PyEventBinder(myEVT_TRAINDONE, 1)

myEVT_GENDONE = wx.NewEventType()
EVT_GENDONE = wx.PyEventBinder(myEVT_GENDONE, 1)

MAX_PLOTS = 4 #increase or decrease depending on number of graphs

class SaveDoneEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, filename=None):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.filename = filename
    def GetName(self):
        return self.filename

class GenDoneEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, data):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.data = data

class TrainDoneEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, data):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.data = data

class TrainWorker(threading.Thread):
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

class SimWorker(threading.Thread):
    def __init__(self, parent, params):

        threading.Thread.__init__(self, daemon=True)
        self.parent = parent
        self.location = params[0]
        self.year_choice = params[1]
        self.terrain_factor = params[2]
        self.latitude = params[3]
        self.longitude = params[4]
        self.windfeatures = params[5]
        self.solarfeatures = params[6]
        self.store_wt_out = params[7][0]
        self.store_sp_out = params[7][1]
        self.store_total_out = params[7][2]
        self.filename = params[8]
        self.sp_eff = params[9]
        self.output_type = params[11] # 0 for simulation, 1 for training

    def run(self):

        sim = Simulator(self.location, self.year_choice, Windturbine(), terrain_factor = self.terrain_factor )
        sim.latitude = self.latitude
        sim.longitude = self.longitude

        if self.store_wt_out:
            P_wt,_ = sim.calc_wind(self.windfeatures)
        else:
            P_wt = 0
        if self.store_sp_out:
            P_sp,_ = sim.calc_solar(Az=self.solarfeatures[2::3], Inc=self.solarfeatures[1::3], sp_area=self.solarfeatures[0::3], sp_eff=self.sp_eff)
        else:
            P_sp = 0
        if self.store_total_out:
            P_tot,_ = sim.calc_total_power(self.solarfeatures, self.windfeatures, self.sp_eff)
        else:
            P_tot = 0

        data = {'Pwt':P_wt,'Psp': P_sp,'Ptot': P_tot}

        self.write_data(data, self.filename)

        evt = SaveDoneEvent(myEVT_SAVEDONE, -1, filename=self.filename)
        wx.PostEvent(self.parent, evt)

    def write_data(self, data, filename):
        
        file_path = filename + ".xlsx"
        if self.output_type == 0:
            if not os.path.isdir('./Simulation output'):
                os.mkdir('./Simulation output') 
            file_path = 'Simulation output' + os.sep + filename + '.xlsx'
        elif self.output_type == 1:
            if not os.path.isdir('./Training output'):
                os.mkdir('./Training output') 
            file_path = 'Training output' + os.sep + filename + '.xlsx'

        data_file = xlw.Workbook(file_path)
        bold = data_file.add_format({'bold': True})

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
        parametersheet.write('B8', 'Rotor height', bold)
        parametersheet.write('C8', self.windfeatures[1])
        parametersheet.write('B10', 'Sp Surface 1', bold)
        parametersheet.write('C10', self.solarfeatures[0])
        parametersheet.write('B11', 'Sp Angle 1', bold)
        parametersheet.write('C11', self.solarfeatures[1])
        parametersheet.write('B12', 'Sp Orientation 1', bold)
        parametersheet.write('C12', self.solarfeatures[2])
        parametersheet.write('B13', 'Sp Surface 2', bold)
        parametersheet.write('C13', self.solarfeatures[3])
        parametersheet.write('B14', 'Sp Angle 2', bold)
        parametersheet.write('C14', self.solarfeatures[4])
        parametersheet.write('B15', 'Sp Orientation 2', bold)
        parametersheet.write('C15', self.solarfeatures[5])
        parametersheet.write('B16', 'Sp Surface 3', bold)
        parametersheet.write('C16', self.solarfeatures[6])
        parametersheet.write('B17', 'Sp Angle 3', bold)
        parametersheet.write('C17', self.solarfeatures[7])
        parametersheet.write('B18', 'Sp Orientation 3', bold)
        parametersheet.write('C18', self.solarfeatures[8])
        parametersheet.write('B19', 'Sp Surface 4', bold)
        parametersheet.write('C19', self.solarfeatures[9])
        parametersheet.write('B20', 'Sp Angle 4', bold)
        parametersheet.write('C20', self.solarfeatures[10])
        parametersheet.write('B21', 'Sp Orientation 4', bold)
        parametersheet.write('C21', self.solarfeatures[11])
        parametersheet.write('B22', 'Sp Efficiency', bold)
        parametersheet.write('C22', self.sp_eff)
        
        datasheet = data_file.add_worksheet('Output data')
        
        demand = np.full(365, 6000)
        data_sized = {'Pwt': 0, 'Psp': 0, 'Ptot': 0}

        datasheet.write('A1', 'Hourly', bold)        
        datasheet.write('E1', 'Daily', bold)
        datasheet.write('A2', 'Pwt', bold)
        datasheet.write('B2', 'Psp', bold)
        datasheet.write('C2', 'Ptot', bold)
        datasheet.write('E2', 'Pwt', bold)
        datasheet.write('F2', 'Psp', bold)
        datasheet.write('G2', 'Ptot', bold)
        datasheet.write('H2', 'Demand', bold)
        datasheet.write_column('H3', demand)

        if self.store_wt_out:
            datasheet.write_column('A3', data['Pwt'])
            data_sized['Pwt'] = np.mean(np.reshape(data['Pwt'], (365,24)), axis=1)
            datasheet.write_column('E3', data_sized['Pwt'])
        
        if self.store_sp_out:
            datasheet.write_column('B3', data['Psp'])
            data_sized['Psp'] = np.mean(np.reshape(data['Psp'], (365,24)), axis=1)
            datasheet.write_column('F3', data_sized['Psp'])
        
        if self.store_total_out:
            datasheet.write_column('C3', data['Ptot'])
            data_sized['Ptot'] = np.mean(np.reshape(data['Ptot'], (365,24)), axis=1)
            datasheet.write_column('G3', data_sized['Ptot'])

        graphsheet = data_file.add_worksheet('Graphs')

        chart = data_file.add_chart({'type': 'line'})
        chart.set_title({'name':'Daily avg. output'})
        chart.set_x_axis({'display units':'days'})
        chart.set_y_axis({'display units':'Output'})

        if self.store_wt_out:
            chart.add_series({
            'values':     '=Output data!$E$3:$E$367',
            'line':       {'color': 'blue'},
            'name': 'Wind'
            })

        if self.store_sp_out:
            chart.add_series({
            'values':     '=Output data!$F$3:$F$367',
            'line':       {'color': 'yellow'},
            'name': 'Solar'
            })

        if self.store_total_out:     
            chart.add_series({
            'values':     '=Output data!$G$3:$G$367',
            'line':       {'color': 'green'},
            'name': 'Total'
            })

        chart.add_series({
        'values':     '=Output data!$H$3:$H$367',
        'line':       {'color': 'red'},
        'name': 'Demand'
        })

        graphsheet.insert_chart( 'B2', chart, { 'x_scale': 3, 'y_scale': 2,})

        graph1 = data_file.add_chart({'type': 'line'})
        graph1.set_title({'name': 'Hourly output graph 1 of 12'})
        graph1.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph1.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph2 = data_file.add_chart({'type': 'line'})
        graph2.set_title({'name': 'Hourly output graph 2 of 12'})
        graph2.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph2.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph3 = data_file.add_chart({'type': 'line'})
        graph3.set_title({'name': 'Hourly output graph 3 of 12'})
        graph3.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph3.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph4 = data_file.add_chart({'type': 'line'})
        graph4.set_title({'name': 'Hourly output graph 4 of 12'})
        graph4.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph4.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph5 = data_file.add_chart({'type': 'line'})
        graph5.set_title({'name': 'Hourly output graph 5 of 12'})
        graph5.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph5.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph6 = data_file.add_chart({'type': 'line'})
        graph6.set_title({'name': 'Hourly output graph 6 of 12'})
        graph6.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph6.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph7 = data_file.add_chart({'type': 'line'})
        graph7.set_title({'name': 'Hourly output graph 7 of 12'})
        graph7.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph7.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph8 = data_file.add_chart({'type': 'line'})
        graph8.set_title({'name': 'Hourly output graph 8 of 12'})
        graph8.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph8.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph9 = data_file.add_chart({'type': 'line'})
        graph9.set_title({'name': 'Hourly output graph 9 of 12'})
        graph9.set_x_axis({ 'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph9.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph10 = data_file.add_chart({'type': 'line'})
        graph10.set_title({'name': 'Hourly output graph 10 of 12'})
        graph10.set_x_axis({'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph10.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})
        
        graph11 = data_file.add_chart({'type': 'line'})
        graph11.set_title({'name': 'Hourly output graph 11 of 12'})
        graph11.set_x_axis({'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph11.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})

        graph12 = data_file.add_chart({'type': 'line'})
        graph12.set_title({'name': 'Hourly output graph 12 of 12'})
        graph12.set_x_axis({'display units':'hours',
                            'name_font': {'size': 14, 'bold': True}})
        graph12.set_y_axis({'display units': 'Output',
                            'name_font': {'size': 14, 'bold': True}})


        if self.store_wt_out:
            graph1.add_series({
            'values': '=Output data!$A$3:$A$733',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph2.add_series({
            'values': '=Output data!$A$733:$A$1463',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph3.add_series({
            'values': '=Output data!$A$1463:$A$2193',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph4.add_series({
            'values': '=Output data!$A$2193:$A$2923',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph5.add_series({
            'values': '=Output data!$A$2923:$A$3653',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph6.add_series({
            'values': '=Output data!$A$3653:$A$4383',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph7.add_series({
            'values': '=Output data!$A$4383:$A$5113',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph8.add_series({
            'values': '=Output data!$A$5113:$A$5843',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph9.add_series({
            'values': '=Output data!$A$5843:$A$6573',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph10.add_series({
            'values': '=Output data!$A$6573:$A$7303',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph11.add_series({
            'values': '=Output data!$A$7303:$A$8033',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
            graph12.add_series({
            'values': '=Output data!$A$8033:$A$8763',
            'line': { 'color': 'blue'},
            'name': 'Wind'
                })
        if self.store_sp_out:
            graph1.add_series({
            'values': '=Output data!$B$3:$B$733',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph2.add_series({
            'values': '=Output data!$B$733:$B$1463',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph3.add_series({
            'values': '=Output data!$B$1463:$B$2193',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph4.add_series({
            'values': '=Output data!$B$2193:$B$2923',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph5.add_series({
            'values': '=Output data!$B$2923:$B$3653',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph6.add_series({
            'values': '=Output data!$B$3653:$B$4383',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph7.add_series({
            'values': '=Output data!$B$4383:$B$5113',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph8.add_series({
            'values': '=Output data!$B$5113:$B$5843',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph9.add_series({
            'values': '=Output data!$B$5843:$B$6573',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph10.add_series({
            'values': '=Output data!$B$6573:$B$7303',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph11.add_series({
            'values': '=Output data!$B$7303:$B$8033',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
            graph12.add_series({
            'values': '=Output data!$B$8033:$B$8763',
            'line': {'color' : 'yellow'},
            'name': 'Solar'
                })
        if self.store_total_out:
            graph1.add_series({
            'values': '=Output data!$C$3:$C$733',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph2.add_series({
            'values': '=Output data!$C$733:$C$1463',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph3.add_series({
            'values': '=Output data!$C$1463:$C$2193',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph4.add_series({
            'values': '=Output data!$C$2193:$C$2923',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph5.add_series({
            'values': '=Output data!$C$2923:$C$3653',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph6.add_series({
            'values': '=Output data!$C$3653:$C$4383',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph7.add_series({
            'values': '=Output data!$C$4383:$C$5113',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph8.add_series({
            'values': '=Output data!$C$5113:$C$5843',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph9.add_series({
            'values': '=Output data!$C$5843:$C$6573',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph10.add_series({
            'values': '=Output data!$C$6573:$C$7303',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph11.add_series({
            'values': '=Output data!$C$7303:$C$8033',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
            graph12.add_series({
            'values': '=Output data!$C$8033:$C$8763',
            'line': { 'color': 'green'},
            'name': 'Total'
                })
        

        graphsheet.insert_chart( 'B34', graph1, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B68', graph2, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B102', graph3, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B136', graph4, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B170', graph5, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B204', graph6, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B238', graph7, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B272', graph8, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B306', graph9, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B340', graph10, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B374', graph11, { 'x_scale': 2, 'y_scale': 2,})
        graphsheet.insert_chart( 'B408', graph12, { 'x_scale': 2, 'y_scale': 2,})


        data_file.close()

class SimTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.locations = [i.lower().capitalize() for i in pd.read_csv('Data/locations.csv',index_col=0,header=0).NAME.values]
        self.location_obj = None
        self.location = None

        self.years = ['0000']

        self.latitude = 0
        self.longitude = 0

        self.sp_price = 160
        self.wt_price = 1070
        self.st_price = 400

        self.store_wt_out = True
        self.store_sp_out = True
        self.store_total_out = True

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

        self.plot_iter = 0

        self.solar_power = None
        self.wind_power = None
        self.total_power = None

        self.solar_energy = None
        self.wind_energy = None
        self.total_energy = None

        self.demand = None
        self.demand_input = 6000

        self.power_surplus = 0
        self.power_shortage = 0
        self.power_storage = 0

        self.cost_calculator = None
 
        self.sol_cost = 0
        self.win_cost = 0 
        self.stor_cost = 0 

        vbox = wx.BoxSizer(wx.VERTICAL)

        locbox = wx.StaticBox(self, -1, 'Location')
        solbox = wx.StaticBox(self, -1, 'Solar options')
        winbox = wx.StaticBox(self, -1, 'Windturbine options')
        storebox = wx.StaticBox(self, -1, 'Save options')
        pricebox = wx.StaticBox(self, -1, 'Cost options')
        canvasbox = wx.StaticBox(self, -1, 'Graph')

        loc_sizer = wx.StaticBoxSizer(locbox, wx.VERTICAL)
        sol_sizer = wx.StaticBoxSizer(solbox, wx.VERTICAL)
        win_sizer = wx.StaticBoxSizer(winbox, wx.VERTICAL)
        store_sizer = wx.StaticBoxSizer(storebox, wx.VERTICAL)
        price_sizer = wx.StaticBoxSizer(pricebox, wx.VERTICAL)
        canvas_sizer = wx.StaticBoxSizer(canvasbox, wx.VERTICAL)

        head_sizer = wx.BoxSizer(wx.HORIZONTAL)

        left_head_sizer = wx.BoxSizer(wx.VERTICAL)
        middle_head_sizer = wx.BoxSizer(wx.VERTICAL)
        right_head_sizer = wx.BoxSizer(wx.VERTICAL)

        hloc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hsol_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hwin_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hstoreSizer = wx.BoxSizer(wx.HORIZONTAL)
        hname_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hpriceSizer = wx.BoxSizer(wx.HORIZONTAL)

        loc_grid = wx.FlexGridSizer(2, 2, 10, 10)
        sol_grid = wx.FlexGridSizer(4, 5, 10, 10)
        win_grid = wx.FlexGridSizer(2, 4, 10, 10)
        price_grid = wx.FlexGridSizer(3, 2, 10, 10)

        self.places = wx.Choice(self, wx.ID_ANY, choices=self.locations)
        self.year_choice = wx.Choice(self, wx.ID_ANY, choices=self.years)

        self.lat_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.latitude))
        self.lon_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.longitude))

        lat_txt = wx.StaticText(self, wx.ID_ANY, 'Latitude ')
        lon_txt = wx.StaticText(self, wx.ID_ANY, 'Longitude ')

        sp_price_txt = wx.StaticText(self, wx.ID_ANY, 'Solar panel (€/m²) ')
        self.sp_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_price))
        wt_price_txt = wx.StaticText(self, wx.ID_ANY, 'Wind turbine (€/kWh) ')
        self.wt_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.wt_price))
        st_price_txt = wx.StaticText(self, wx.ID_ANY, 'Storage (€/kWh) ')
        self.st_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.st_price))

        sp_eff_text = wx.StaticText(self, wx.ID_ANY, 'Panel efficiency(%) ')
        self.sp_eff_field = wx.TextCtrl(self, wx.ID_ANY, value = str(self.sp_eff))
        area_txt = wx.StaticText(self, wx.ID_ANY, 'Surface ')
        self.area_field1 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_area_1))
        self.area_field2 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_area_2))
        self.area_field3 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_area_3))
        self.area_field4 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_area_4))

        angle_txt = wx.StaticText(self, wx.ID_ANY, 'Angle ')
        self.angle_field1 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_ang_1))
        self.angle_field2 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_ang_2))
        self.angle_field3 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_ang_3))
        self.angle_field4 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_ang_4))

        or_txt = wx.StaticText(self, wx.ID_ANY, 'Orientation ')
        self.or_field1 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_or_1))
        self.or_field2 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_or_2))
        self.or_field3 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_or_3))
        self.or_field4 = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_or_4))

        nwt_txt = wx.StaticText(self, wx.ID_ANY, 'Number of turbines ')
        self.nwt_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.n_wt))
        wth_txt = wx.StaticText(self, wx.ID_ANY, 'Turbine height ')
        self.wth_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.wt_height))
        ter_txt = wx.StaticText(self, wx.ID_ANY, 'Terrain factor ')
        self.ter_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.terrain_factor))
        wt_type_txt = wx.StaticText(self, wx.ID_ANY, 'Type: ')
        wt_path = 'config' + os.sep + 'turbines'
        self.wt_type_choice = wx.Choice(self, wx.ID_ANY, choices=[os.path.splitext(n)[0] for n in os.listdir(wt_path) if '.csv' in n])

        self.wt_out = wx.CheckBox(self, wx.ID_ANY, 'Turbinepower ')
        self.wt_out.SetValue(True)
        self.sp_out = wx.CheckBox(self, wx.ID_ANY, 'Solarpower ')
        self.sp_out.SetValue(True)
        self.total_out = wx.CheckBox(self, wx.ID_ANY, 'Total power ')
        self.total_out.SetValue(True)
        filename_txt = wx.StaticText(self, wx.ID_ANY, 'Filename: ')
        self.filename_field = wx.TextCtrl(self, wx.ID_ANY, 'Sim_output')

        self.save_button = wx.Button(self, wx.ID_ANY, label='Save simulation')
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_button_clicked)

        self.places.Bind(wx.EVT_CHOICE, self.on_location_picked)
        self.sp_out.Bind(wx.EVT_CHECKBOX, self.on_checkbox_ticked)
        self.wt_out.Bind(wx.EVT_CHECKBOX, self.on_checkbox_ticked)
        self.total_out.Bind(wx.EVT_CHECKBOX, self.on_checkbox_ticked)

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
        graph_button_sizer.AddMany([(self.previousgraph_button, 1, wx.ALL, 2), (self.nextgraph_button, 1, wx.ALL, 2),
                                    (self.simulate_button, 1, wx.ALL, 2)])
        canvas_sizer.Add(graph_button_sizer, 0, wx.ALL, 2)
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
        
        
        store_sizer.AddMany([(self.wt_out, 0, wx.ALL, 8), (self.sp_out, 0, wx.ALL, 8), 
                             (self.total_out, 0, wx.ALL, 8)])
        hname_sizer.AddMany([(filename_txt, 0, wx.ALL, 8), (self.filename_field, 0, wx.ALL, 8),
                            (self.save_button, 0, wx.ALL, 8)])

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
        store_sizer.Add(hname_sizer, 0, wx.ALL, 2)

        left_head_sizer.Add(loc_sizer, 0, wx.ALL, 4)
        left_head_sizer.Add(price_sizer, 0, wx.ALL|wx.GROW, 4)
        middle_head_sizer.Add(sol_sizer, 0, wx.ALL, 4)
        middle_head_sizer.Add(win_sizer, 0, wx.ALL, 4)
        right_head_sizer.Add(store_sizer, 0, wx.ALL, 4)

        head_sizer.Add(left_head_sizer, 0, wx.ALL, 2)
        head_sizer.Add(middle_head_sizer, 0, wx.ALL, 2)
        head_sizer.Add(right_head_sizer, 0, wx.ALL, 2)


        vbox.Add(head_sizer, 0, wx.ALL, 2)
        vbox.Add(canvas_sizer, 0, wx.ALL|wx.GROW, 2)

        self.SetSizer(vbox)

    def on_simulate_clicked(self, event):
        turbine = Windturbine(self.wt_type_choice.GetString(self.wt_type_choice.GetCurrentSelection()))
        simulator = Simulator(self.location_obj, self.year_choice.GetString(self.year_choice.GetCurrentSelection()), 
                              turbine, latitude=self.latitude, longitude=self.longitude)
        self.solar_power, self.solar_energy = simulator.calc_solar(Az=[self.sp_or_1, self.sp_or_2, self.sp_or_3, self.sp_or_4], 
                                                                   Inc=[self.sp_ang_1, self.sp_ang_2, self.sp_ang_3, self.sp_ang_4], 
                                                                   sp_area=[self.sp_area_1, self.sp_area_2, self.sp_area_3, self.sp_area_4], sp_eff=self.sp_eff)
        self.wind_power, self.wind_energy = simulator.calc_wind([self.n_wt, self.wt_height])
        self.total_power = self.wind_power + self.solar_power
        self.total_energy = self.wind_energy + self.solar_energy

        self.demand_input = 6000
        self.demand = np.full(len(self.total_power), self.demand_input)

        self.cost_calculator = CostCalculator(self.sp_price, self.st_price, self.demand_input, 0, self.wt_price, 0, True, windturbine=turbine)
        stats = self.cost_calculator.get_stats(self.total_power, np.sum([self.sp_area_1, self.sp_area_2, self.sp_area_3, self.sp_area_4]), self.n_wt)


        self.power_surplus = stats['total_surplus']
        self.power_storage = stats['total_storage']
        self.power_shortage = stats['total_shortage']
        self.sol_cost = stats['solar_cost']
        self.win_cost = stats['wind_cost']
        self.stor_cost = stats['storage_cost']

        self.draw()

    def on_prev_clicked(self, event):

        if self.plot_iter == 0:
            self.plot_iter = MAX_PLOTS
        else:
            self.plot_iter -= 1
        self.draw()

    def on_next_clicked(self, event):
        
        if self.plot_iter == MAX_PLOTS:
            self.plot_iter = 0
        else:
            self.plot_iter += 1
        self.draw()
    
    def draw(self):

        self.axes.clear()

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

    def on_location_picked(self, event):
        self.location = self.places.GetString(self.places.GetSelection())
        self.location_obj = Location(self.location)
        self.years = self.location_obj.get_years()
        self.years = np.flip(self.years)
        self.update_fields()

    def on_checkbox_ticked(self, event):
        self.store_wt_out = self.wt_out.GetValue()
        self.store_sp_out = self.sp_out.GetValue()
        self.store_total_out = self.total_out.GetValue()

    def update_fields(self):
        self.year_choice.Clear()
        self.year_choice.AppendItems(self.years)

        self.lat_field.SetValue(str('%.3f'%self.location_obj.latitude))
        self.lon_field.SetValue(str('%.3f'%self.location_obj.longitude))
        self.ter_field.SetValue(str('%.3f'%self.location_obj.terrain))
    
    def on_fieldbox_changed(self, event):
        #throws warning when field is empty(duh)
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

    def on_save_button_clicked(self, event):
        
        windfeatures = [int(self.n_wt), int(self.wt_height)]
        solarfeatures = [float(self.sp_area_1), float(self.sp_ang_1), float(self.sp_or_1), 
                         float(self.sp_area_2), float(self.sp_ang_2), float(self.sp_or_2),
                         float(self.sp_area_3), float(self.sp_ang_3), float(self.sp_or_3),
                         float(self.sp_area_4), float(self.sp_ang_4), float(self.sp_or_4)]
        store_params = [self.store_wt_out, self.store_sp_out, self.store_total_out]
        price_params = [self.sp_price, self.wt_price, self.st_price]
        parameters = [self.location_obj, self.year_choice.GetString(self.year_choice.GetCurrentSelection()), self.terrain_factor, 
                      self.latitude, self.longitude, windfeatures, solarfeatures, store_params, 
                      self.filename_field.GetValue(), self.sp_eff, price_params, 0]
        worker = SimWorker(self, parameters)
        worker.start()
        self.save_button.Disable()

    def on_savedone(self, evt):
        filename = evt.GetName()

        file_info = 'Simulation stored in ' + filename + '.xlsx'
        wx.MessageBox(file_info, 'Saving done', wx.OK)
        self.save_button.Enable()

class InputDialog(wx.Dialog):
    """
        Dialog for setting inputs in the training.
    """
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="Inputs")

        self.parent= parent
        self.locations = [i.lower().capitalize() for i in pd.read_csv('Data/locations.csv',index_col=0, header=0).NAME.values]
        self.years = ['0000']

        self.latitude = 0
        self.longitude = 0
        self.terrain_factor = 0

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

        self.demand = 0

        self.generations = 0
        self.poolsize = 0
        self.m_rate = 0

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
        self.lat_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.latitude))
        self.lon_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.longitude))

        #Labels for lat and lon
        lat_txt = wx.StaticText(self, wx.ID_ANY, 'Latitude ')
        lon_txt = wx.StaticText(self, wx.ID_ANY, 'Longitude ')

        loc_grid.AddMany([(lat_txt, 0, wx.ALL, 2), (self.lat_field, 0, wx.ALL, 2),
                          (lon_txt, 0, wx.ALL, 2), (self.lon_field, 0, wx.ALL, 2)])

        hloc_sizer.AddMany([(self.places, 0, wx.ALL, 2),(self.year_choice, 0, wx.ALL, 2)])

        #Solar options
        sp_eff_txt = wx.StaticText(self, wx.ID_ANY, 'Panel efficiency ')
        self.sp_eff_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_eff), name='sp_eff')
        sp_area_min_txt = wx.StaticText(self, wx.ID_ANY, 'Surface min ')
        self.sp_area_min_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_area_min), name='sp_area_min')
        sp_area_max_txt = wx.StaticText(self, wx.ID_ANY, 'Surface max ')
        self.sp_area_max_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_area_max), name='sp_area_max')
        sp_ang_min_txt = wx.StaticText(self, wx.ID_ANY, 'Angle min ')
        self.sp_ang_min_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_ang_min), name='sp_ang_min')
        sp_ang_max_txt = wx.StaticText(self, wx.ID_ANY, 'Angle max ')
        self.sp_ang_max_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_ang_max), name='sp_ang_max')
        sp_or_min_txt = wx.StaticText(self, wx.ID_ANY, 'Orientation min ')
        self.sp_or_min_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_or_min), name='sp_or_min')
        sp_or_max_txt = wx.StaticText(self, wx.ID_ANY, 'Orientation max ')
        self.sp_or_max_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_or_max), name='sp_or_max')

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
        self.wtn_min_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.wtn_min), name='wtn_min')
        wtn_max_txt = wx.StaticText(self, wx.ID_ANY, 'Maximum turbines ')
        self.wtn_max_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.wtn_max), name='wtn_max')
        turbine_height_txt = wx.StaticText(self, wx.ID_ANY, 'Turbine height ')
        self.turbine_height_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.turbine_height), name='turbine_height')
        ter_txt = wx.StaticText(self, wx.ID_ANY, 'Terrain factor ')
        self.ter_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.terrain_factor), name='terrain_factor')
        wt_type_txt = wx.StaticText(self, wx.ID_ANY, 'Type: ')
        wt_path= 'config' + os.sep + 'turbines'
        self.wt_type_choice= wx.Choice(self, wx.ID_ANY, choices=[os.path.splitext(n)[0] for n in os.listdir(wt_path) if '.csv' in n])

        win_input_grid.AddMany([(wtn_min_txt, 0, wx.ALL, 2), (self.wtn_min_field, 0, wx.ALL, 2),
                                (wtn_max_txt, 0, wx.ALL, 2), (self.wtn_max_field, 0, wx.ALL, 2),
                                (turbine_height_txt, 0, wx.ALL, 2), (self.turbine_height_field, 0, wx.ALL, 2),
                                (ter_txt, 0, wx.ALL, 2), (self.ter_field, 0, wx.ALL, 2),
                                (wt_type_txt, 0, wx.ALL, 2), (self.wt_type_choice, 0, wx.ALL, 2)])

        #Genetic algorithm options
        demand_txt = wx.StaticText(self, wx.ID_ANY, 'Demand ')
        self.demand_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.demand), name='demand')
        generations_txt = wx.StaticText(self, wx.ID_ANY, 'Generations ')
        self.generations_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.generations), name='generations')
        poolsize_txt = wx.StaticText(self, wx.ID_ANY, 'Poolsize ')
        self.poolsize_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.poolsize), name='pool_size')
        m_rate_txt = wx.StaticText(self, wx.ID_ANY, 'Mutation rate ')
        self.m_rate_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.m_rate), name='mutation_rate')

        ga_grid.AddMany([(demand_txt, 0, wx.ALL, 2), (self.demand_field, 0, wx.ALL, 2), (m_rate_txt, 0, wx.ALL, 2),
                         (self.m_rate_field, 0, wx.ALL, 2), (generations_txt, 0, wx.ALL, 2), (self.generations_field, 0, wx.ALL, 2),
                         (poolsize_txt, 0, wx.ALL, 2), (self.poolsize_field, 0, wx.ALL, 2)])

        #Price options. Trainby is to input wether algoritm trains by power output or price of configuration
        trainby_txt = wx.StaticText(self, wx.ID_ANY, 'Train by: ')
        self.power_check = wx.RadioButton(self, wx.ID_ANY, 'Power')
        self.price_check = wx.RadioButton(self, wx.ID_ANY, 'Price')

        self.sp_price_txt = wx.StaticText(self, wx.ID_ANY, 'Solar panel (€/m²) ')
        self.sp_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.sp_price), name='solar_panel_price')
        self.wt_price_txt = wx.StaticText(self, wx.ID_ANY, 'Wind turbine (€/kWh) ')
        self.wt_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.wt_price), name='wind_turbine_price')
        self.st_price_txt = wx.StaticText(self, wx.ID_ANY, 'Storage (€/kWh)')
        self.st_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.st_price), name='storage_price')
        self.short_price_txt = wx.StaticText(self, wx.ID_ANY, 'Shortage (€/kWh) ')
        self.short_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.shortage_price), name='shortage_price')
        self.surplus_price_txt = wx.StaticText(self, wx.ID_ANY, 'Surplus price (€/kWh) ')
        self.surplus_price_field = wx.TextCtrl(self, wx.ID_ANY, value=str(self.surplus_price), name='surplus_price')

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
        event_object.SetToolTipString(field_info(event_object.GetName()))

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
            Loads defaults (duh)
        """
        self.load_defaults()

    def on_save_default_clicked(self, event):
        """
            Saves values as default
        """
        self.save_default()

    def on_check_clicked(self, event):
        if(self.price_check.GetValue()):
            self.price_grid.Hide(self.surplus_price_txt)
            self.price_grid.Hide(self.surplus_price_field)
            self.price_grid.Show(self.sp_price_txt)
            self.price_grid.Show(self.sp_price_field)
            self.price_grid.Show(self.wt_price_txt)
            self.price_grid.Show(self.wt_price_field)

        if(self.power_check.GetValue()):
            self.price_grid.Show(self.surplus_price_txt)
            self.price_grid.Show(self.surplus_price_field)
            self.price_grid.Hide(self.sp_price_txt)
            self.price_grid.Hide(self.sp_price_field)
            self.price_grid.Hide(self.wt_price_txt)
            self.price_grid.Hide(self.wt_price_field)
            
        self.price_grid.Layout()
        self.Layout()

    def update_loc_settings(self):
        """
            Updates the location settings. Gets called when a location is picked.
        """
        self.year_choice.Clear()
        self.year_choice.AppendItems(self.years)

        self.lat_field.SetValue(str('%.3f'%self.location_obj.latitude))
        self.lon_field.SetValue(str('%.3f'%self.location_obj.longitude))
        self.ter_field.SetValue(str('%.3f'%self.location_obj.terrain))

    def update_fields(self):
        """
            Updates all the fields to the value that is stored in the corresponding value.
            Gets called when configs are loaded or when the 'cancel' button is clicked
        """
        self.lat_field.SetValue(str('%.3f'%self.latitude))
        self.lon_field.SetValue(str('%.3f'%self.longitude))

        self.sp_eff_field.SetValue(str(self.sp_eff))
        self.sp_area_min_field.SetValue(str(self.sp_area_min))
        self.sp_area_max_field.SetValue(str(self.sp_area_max))
        self.sp_ang_min_field.SetValue(str(self.sp_ang_min))
        self.sp_ang_max_field.SetValue(str(self.sp_ang_max))
        self.sp_or_min_field.SetValue(str(self.sp_or_min))
        self.sp_or_max_field.SetValue(str(self.sp_or_max))

        self.wtn_min_field.SetValue(str(self.wtn_min))
        self.wtn_max_field.SetValue(str(self.wtn_max))
        self.turbine_height_field.SetValue(str(self.turbine_height))
        self.ter_field.SetValue(str('%.3f'%self.terrain_factor))

        self.demand_field.SetValue(str(self.demand))

        self.generations_field.SetValue(str(self.generations))
        self.poolsize_field.SetValue(str(self.poolsize))
        self.m_rate_field.SetValue(str(self.m_rate))

        self.sp_price_field.SetValue(str(self.sp_price))
        self.wt_price_field.SetValue(str(self.wt_price))
        self.st_price_field.SetValue(str(self.st_price))
        self.short_price_field.SetValue(str(self.shortage_price))
        self.surplus_price_field.SetValue(str(self.surplus_price))

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
        defaults = pd.read_csv('config' + os.sep + 'defaults' + os.sep + 'train_defaults.csv', header=0)

        self.places.SetSelection(defaults.location_choice.values[0])
        self.on_location_picked(None)
        self.year_choice.SetSelection(defaults.year_choice.values[0])
        self.n_sp_configs_list.SetSelection(defaults.n_sp_configs_choice.values[0])

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
                    'wtn_min': self.wtn_min, 'wtn_max': self.wtn_max,
                    'demand': self.demand, 'generations': self.generations, 
                    'poolsize': self.poolsize, 'm_rate': self.m_rate, 
                    'sp_price': self.sp_price, 'wt_price': self.wt_price, 
                    'st_price': self.st_price, 'shortage_price': self.shortage_price, 'surplus_price': self.surplus_price,
                    'n_config_':self.n_sp_configs,'year_choice':self.year_choice.GetCurrentSelection(),
                    'location_choice':self.places.GetCurrentSelection(),'n_sp_configs_choice':self.n_sp_configs_list.GetCurrentSelection()}
        pd.DataFrame([defaults]).to_csv('config' + os.sep + 'defaults' + os.sep + 'train_defaults.csv')

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
        self.years= ['0000']

        self.dialog = InputDialog(self)

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

        self.n_sp_configs = 4

        self.costcalculator = None
        self.simulator = None

        self.plot_iter = 0

        self.store_wt_out = True
        self.store_sp_out = True
        self.store_total_out = True

        self.config = None
        self.train_worker = None

        self.Bind(EVT_GENDONE, self.on_gendone)
        self.Bind(EVT_TRAINDONE, self.on_training_done)
        self.Bind(EVT_SAVEDONE, self.on_savedone)
        
        vbox = wx.BoxSizer(wx.VERTICAL)

        sol_output_box = wx.StaticBox(self, -1, 'Solar panel outputs')
        win_output_box = wx.StaticBox(self, -1, 'Windturbine outputs')
        stat_box = wx.StaticBox(self, -1, 'Power statistics')
        cost_box = wx.StaticBox(self, -1, 'Cost statistics')
        canvas_box = wx.StaticBox(self, -1, 'Graph')
        save_box = wx.StaticBox(self, -1, 'Save options')

        sol_output_sizer = wx.StaticBoxSizer(sol_output_box, wx.VERTICAL)
        win_output_sizer = wx.StaticBoxSizer(win_output_box, wx.VERTICAL)
        stat_sizer = wx.StaticBoxSizer(stat_box, wx.VERTICAL)
        canvas_sizer = wx.StaticBoxSizer(canvas_box, wx.VERTICAL)
        cost_sizer = wx.StaticBoxSizer(cost_box, wx.VERTICAL)
        save_sizer = wx.StaticBoxSizer(save_box, wx.VERTICAL)

        input_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filename_sizer = wx.BoxSizer(wx.HORIZONTAL)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_left_sizer = wx.BoxSizer(wx.VERTICAL)
        top_middle_sizer = wx.BoxSizer(wx.VERTICAL)
        top_right_sizer = wx.BoxSizer(wx.VERTICAL)

        sol_output_grid = wx.FlexGridSizer(3, 5, 10, 10)
        win_output_grid = wx.FlexGridSizer(2, 2, 10, 10)
        stat_grid = wx.FlexGridSizer(3, 2, 10, 10)
        cost_grid = wx.FlexGridSizer(3, 2, 10, 10)

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

        self.wt_out_check = wx.CheckBox(self, wx.ID_ANY, 'Turbinepower ')
        self.wt_out_check.SetValue(True)
        self.sp_out_check = wx.CheckBox(self, wx.ID_ANY, 'Solarpower ')
        self.sp_out_check.SetValue(True)
        self.total_out_check = wx.CheckBox(self, wx.ID_ANY, 'Total power ')
        self.total_out_check.SetValue(True)
        filename_txt = wx.StaticText(self, wx.ID_ANY, 'Filename: ')
        self.filename_field = wx.TextCtrl(self, wx.ID_ANY, value='Training_output')

        self.sp_out_check.Bind(wx.EVT_CHECKBOX, self.on_checkbox_ticked)
        self.wt_out_check.Bind(wx.EVT_CHECKBOX, self.on_checkbox_ticked)
        self.total_out_check.Bind(wx.EVT_CHECKBOX, self.on_checkbox_ticked)

        progress_txt = wx.StaticText(self, wx.ID_ANY, 'Progress: ')
        self.progress = wx.Gauge(self, size=(400,20))
        
        sp_area_txt = wx.StaticText(self, wx.ID_ANY, 'Surfaces ')
        self.sp_area_1_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_area_1))
        self.sp_area_2_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_area_2))
        self.sp_area_3_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_area_3))
        self.sp_area_4_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_area_4))

        sp_ang_txt = wx.StaticText(self, wx.ID_ANY, 'Angles ')
        self.sp_ang_1_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_ang_1))
        self.sp_ang_2_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_ang_2))
        self.sp_ang_3_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_ang_3))
        self.sp_ang_4_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_ang_4))

        sp_or_txt = wx.StaticText(self, wx.ID_ANY, 'Orientations ')
        self.sp_or_1_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_or_1))
        self.sp_or_2_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_or_2))
        self.sp_or_3_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_or_3))
        self.sp_or_4_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sp_or_4))

        sol_output_grid.AddMany([(sp_area_txt, 0, wx.ALL, 2), (self.sp_area_1_field, 0, wx.ALL, 2), (self.sp_area_2_field, 0, wx.ALL, 2), 
                                 (self.sp_area_3_field, 0, wx.ALL, 2), (self.sp_area_4_field, 0, wx.ALL, 2),
                                 (sp_ang_txt, 0, wx.ALL, 2), (self.sp_ang_1_field, 0, wx.ALL, 2), (self.sp_ang_2_field, 0, wx.ALL, 2), 
                                 (self.sp_ang_3_field, 0, wx.ALL, 2), (self.sp_ang_4_field, 0, wx.ALL, 2),
                                 (sp_or_txt, 0, wx.ALL, 2), (self.sp_or_1_field, 0, wx.ALL, 2), (self.sp_or_2_field, 0, wx.ALL, 2), 
                                 (self.sp_or_3_field, 0, wx.ALL, 2), (self.sp_or_4_field, 0, wx.ALL, 2)])

        wt_n_txt = wx.StaticText(self, wx.ID_ANY, 'Turbines ')
        self.wtn_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.n_wt))
        wt_h_txt = wx.StaticText(self, wx.ID_ANY, 'Turbine height (m) ')
        self.wth_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.wt_height))

        storage_txt = wx.StaticText(self, wx.ID_ANY, 'Power storage (kWh) ')
        self.storage_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.power_storage))
        surplus_txt = wx.StaticText(self, wx.ID_ANY, 'Power surplus (kWh) ')
        self.surplus_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.power_surplus))
        shortage_txt = wx.StaticText(self, wx.ID_ANY, 'Power shortage (kWh) ')
        self.shortage_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.power_shortage))

        sol_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Solar cost (€) ')
        self.sol_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.sol_cost))
        win_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Wind cost (€) ')
        self.win_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.win_cost))
        stor_cost_txt = wx.StaticText(self, wx.ID_ANY, 'Storage cost (€) ')
        self.stor_cost_field = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY, value=str(self.stor_cost))

        # Plot setup
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)

        graph_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        graph_button_sizer.AddMany([(self.previousgraph_button, 0, wx.ALL, 2), (self.nextgraph_button, 0, wx.ALL, 2)])
        canvas_sizer.Add(graph_button_sizer, 0, wx.ALL, 2)
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
                           (stor_cost_txt, 0, wx.ALL, 2), (self.stor_cost_field, 0, wx.ALL, 2)])

        sol_output_sizer.Add(sol_output_grid, 0, wx.ALL, 2)
        win_output_sizer.Add(win_output_grid, 0, wx.ALL, 2)
        stat_sizer.Add(stat_grid, 0, wx.ALL, 2)
        cost_sizer.Add(cost_grid, 0, wx.ALL, 2)
        filename_sizer.AddMany([(filename_txt, 0 , wx.ALL, 8), (self.filename_field, 0 , wx.ALL, 8),
                                (self.save_button, 0 , wx.ALL, 8)])
        save_sizer.AddMany([(self.sp_out_check, 0, wx.ALL, 8),(self.wt_out_check, 0, wx.ALL, 8),
                            (self.total_out_check, 0 , wx.ALL, 8),(filename_sizer, 0 , wx.ALL, 0)])

        top_left_sizer.Add(sol_output_sizer, 0, wx.ALL, 2)
        top_left_sizer.Add(win_output_sizer, 0, wx.ALL, 2)

        top_middle_sizer.Add(stat_sizer, 0, wx.ALL, 2)
        top_middle_sizer.Add(cost_sizer, 0, wx.ALL, 2)

        top_right_sizer.Add(save_sizer, 0, wx.ALL, 2)

        top_sizer.AddMany([(top_left_sizer, 0, wx.ALL, 0),
                           (top_middle_sizer, 0, wx.ALL, 0),
                           (top_right_sizer, 0, wx.ALL, 0)])

        vbox.Add(input_button_sizer, 0, wx.ALL, 4)
        vbox.Add(top_sizer, 0, wx.ALL, 2)

        vbox.Add(canvas_sizer, 0, wx.ALL|wx.GROW, 2)

        self.SetSizer(vbox)
        self.Fit()

    def on_prev_clicked(self, event):

        if self.plot_iter == 0:
            self.plot_iter = MAX_PLOTS
        else:
            self.plot_iter -= 1
        self.draw()

    def on_next_clicked(self, event):
        
        if self.plot_iter == MAX_PLOTS:
            self.plot_iter = 0
        else:
            self.plot_iter += 1
        self.draw()

    def update_outputs(self):

        self.sp_area_1_field.SetValue(str(self.sp_area_1))
        self.sp_area_2_field.SetValue(str(self.sp_area_2))
        self.sp_area_3_field.SetValue(str(self.sp_area_3))
        self.sp_area_4_field.SetValue(str(self.sp_area_4))

        self.sp_ang_1_field.SetValue(str(self.sp_ang_1))
        self.sp_ang_2_field.SetValue(str(self.sp_ang_2))
        self.sp_ang_3_field.SetValue(str(self.sp_ang_3))
        self.sp_ang_4_field.SetValue(str(self.sp_ang_4))

        self.sp_or_1_field.SetValue(str(self.sp_or_1))
        self.sp_or_2_field.SetValue(str(self.sp_or_2))
        self.sp_or_3_field.SetValue(str(self.sp_or_3))
        self.sp_or_4_field.SetValue(str(self.sp_or_4))

        self.wtn_field.SetValue(str(self.n_wt))
        self.wth_field.SetValue(str(self.wt_height))

        self.storage_field.SetValue(str(int(self.power_storage)))
        self.surplus_field.SetValue(str(int(self.power_surplus)))
        self.shortage_field.SetValue(str(int(self.power_shortage)))

        self.sol_cost_field.SetValue(str(int(self.sol_cost)))
        self.win_cost_field.SetValue(str(int(self.win_cost)))
        self.stor_cost_field.SetValue(str(int(self.stor_cost)))

    def on_checkbox_ticked(self, event):
        self.store_wt_out = self.wt_out_check.GetValue()
        self.store_sp_out = self.sp_out_check.GetValue()
        self.store_total_out = self.total_out_check.GetValue()

    def on_inputbutton_clicked(self, event):
        self.dialog.Show(show=1)

    def on_start_clicked(self, event):

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
                      'mutation_percentage':self.dialog.m_rate, 'turbines_min':self.dialog.wtn_min, 
                      'turbines_max':self.dialog.wtn_max, 'turbine_height':self.dialog.turbine_height, 
                      'cost_calculator':self.costcalculator, 
                      'simulator':self.simulator, 
                      'sp_eff':16}

        self.train_worker = TrainWorker(self, parameters)
        self.train_worker.start()
        self.start_button.Disable()

    def on_stop_clicked(self, event):
        self.train_worker.stop()
        self.progress.SetValue(0)
        self.start_button.Enable()

    def on_gendone(self, event):
        self.progress.SetValue(event.data[1]+1)
        self.config = event.data[0].astype(int)
        solar_features = self.config[:12]
        turbines = self.config[12]

        surface_features = solar_features[0::3]
        angle_features = solar_features[1::3]
        orientation_features = solar_features[2::3]
        
        self.sp_area_1 = surface_features[0]
        self.sp_area_2 = surface_features[1]
        self.sp_area_3 = surface_features[2]
        self.sp_area_4 = surface_features[3]
        self.sp_or_1 = orientation_features[0]
        self.sp_or_2 = orientation_features[1]
        self.sp_or_3 = orientation_features[2]
        self.sp_or_4 = orientation_features[3]
        self.sp_ang_1 = angle_features[0]
        self.sp_ang_2 = angle_features[1]
        self.sp_ang_3 = angle_features[2]
        self.sp_ang_4 = angle_features[3]
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
        self.sol_cost = stats['solar_cost']
        self.win_cost = stats['wind_cost']
        self.stor_cost = stats['storage_cost']

        self.update_outputs()

        self.draw()

    def draw(self):

        self.axes.clear()

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

    def on_save_clicked(self, event):
        
        windfeatures = [int(self.n_wt), int(self.wt_height)]
        solarfeatures = [float(self.sp_area_1), float(self.sp_ang_1), float(self.sp_or_1), 
                         float(self.sp_area_2), float(self.sp_ang_2), float(self.sp_or_2),
                         float(self.sp_area_3), float(self.sp_ang_3), float(self.sp_or_3),
                         float(self.sp_area_4), float(self.sp_ang_4), float(self.sp_or_4)]
        store_params = [self.store_wt_out, self.store_sp_out, self.store_total_out]
        price_params = [self.dialog.sp_price, self.dialog.wt_price, self.dialog.st_price]
        parameters = [Location(self.dialog.location), self.dialog.year_choice.GetString(self.dialog.year_choice.GetCurrentSelection()), self.dialog.terrain_factor, 
                      self.dialog.latitude, self.dialog.longitude, windfeatures, solarfeatures, store_params, 
                      self.filename_field.GetValue(), self.dialog.sp_eff, price_params, 1]
        worker = SimWorker(self, parameters)
        worker.start()
        self.save_button.Disable()

    def on_savedone(self, evt):
        filename = evt.GetName()

        file_info = 'Training output stored in ' + filename + '.xlsx'
        wx.MessageBox(file_info, 'Saving done', wx.OK)
        
        self.save_button.Enable()

    def on_training_done(self, evt):
        
        file_info = 'Training done for ' + self.dialog.location + ' ' + self.dialog.year_choice.GetString(self.dialog.year_choice.GetSelection())
        wx.MessageBox(file_info, 'Training done', wx.OK)

        self.progress.SetValue(0)
        self.start_button.Enable()

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="Simtool")

        nb = wx.Notebook(self)

        tab1 = SimTab(nb)
        tab2 = TrainTab(nb)

        nb.AddPage(tab1, "Simulation")
        nb.AddPage(tab2, "Training")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(nb, 1, wx.ALL|wx.EXPAND, 2)

        self.SetSizer(sizer)
        self.Layout()
        self.Fit()
        self.Maximize(True)

if __name__ == "__main__":
    app = wx.App()
    MainFrame().Show()
    app.MainLoop()