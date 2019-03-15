#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 13:28:34 2019

@author: daniel
"""
import pyomo
import pyomo.opt
from pyomo.environ import *
# Possible to import pyomo.environ as pe and use pe.() for Param, Set, Var, ... Pyomo classes.
import pandas as pd
### import numpy as np
# Panda has been able to deal with data, not necessary to use Numpy so far.

class WIP:
    """This class implements a single-user multi-period Optimal Power Flow.
    
    Household parameters: solar generation and load demand curve.
        These are read from a csv file, upon initialization (__init__).
        Other parameters included in .csv: cost curve.
    Remaining parameters: battery and temporal, initialized/defaulted with values within code.
    
    Variables: battery as flexible storage, active power import from grid.
        (xPlus and xMinus are non-negative and compose xGrid = xPlus - xMinus.)
    
    Next steps: multiple households, then include network parameters. Then, solve w/ ADMM...
    """
    def __init__(self,consumerfile):
        self.consumer_data = pd.read_csv(consumerfile)
        # Reading CSV files with Pandas
        self.consumer_data.columns = self.consumer_data.columns.str.strip() #Removes spaces from header
        # Defining index for sets:
        self.consumer_data.set_index('T',inplace=True) #Performs indexing of column 'T' in place, i.e. on the run
        # Defining data for sets
        self.T_set = self.consumer_data.index.unique() # Unique indexes are preserved, but not reordered.
        # Calls function to create the whole model (concrete, not abstract model)
        self.createModel()
    
    def createModel(self):
        ### Defines ConcreteModel within Pyomo environment (Alternatively: pe.ConcreteModel())
        self.model = ConcreteModel()

        ### Sets ###
        # Creates set T based on csv file
        self.model.T = Set(initialize=self.T_set)
        # Excludes first time period, or zero, to create T2 set
        self.model.T2 = Set(initialize = self.model.T - [0])
        # Motif: used with time = k+1, previous updates, not battery initial SoC
        
        ### Parameters ###
        # Temporal parameters
        """ Modify: read and calculate from CSV data! """
        self.model.t0     = Param(default=0.0)
        self.model.tend   = Param(initialize=23.5)
        self.model.delta  = Param(default=0.5)

        # Cost parameters
        def init_c0(model,j):
            return self.consumer_data.loc[j, 'c0']
        def init_c1(model,i):
            return self.consumer_data.ix[i, 'c1']
        def init_c2(model,i):
            return self.consumer_data.ix[i, 'c2']
        self.model.c2     = Param(self.model.T, initialize = init_c2)
        self.model.c1     = Param(self.model.T, initialize = init_c1)
        self.model.c0     = Param(self.model.T, initialize = init_c0)
        
        # Local demand and generation inputs
        def init_demP(model,j):
            return self.consumer_data.loc[j, 'demP']
        def init_genP(model,i):
            return self.consumer_data.ix[i, 'genP']
        self.model.genP   = Param(self.model.T, initialize = init_genP)
        self.model.demP   = Param(self.model.T, initialize = init_demP)
        # If loads have reactive power:
        #model.demQ
        
        # Battery parameters
        """ Possibly include in a separate 'control' file instead of in-line initializations """
        self.model.bmin   = Param(initialize=1.75)
        self.model.bmax   = Param(initialize=1.75)
        self.model.cmin   = Param(initialize=0)
        self.model.cmax   = Param(initialize=7.5)
        self.model.soc0   = Param(initialize=3)
        self.model.etab   = Param(initialize=0.92)
        
        ### Decision variables ###
        self.model.xPlus     = Var(self.model.T, within=NonNegativeReals)
        self.model.xMinus    = Var(self.model.T, within=NonNegativeReals)
        self.model.xGrid     = Var(self.model.T)
        self.model.bSoC      = Var(self.model.T, bounds=(self.model.cmin,self.model.cmax))
        """Network model will include reactive power; batteries power flow"""
        #model.xQ
        #model.xBat!
        # Create xPV (as parameter???)?, xHouse (demP???)?,, ...
        
        ########################### Objective and constraints ###########################
        ### Objective function: Minimize import cost of household
        def cost_rule(model):
            return sum((((self.model.xPlus[i])**2)*(self.model.c2[i]) + self.model.c1[i]*self.model.xPlus[i] + self.model.c0[i]) for i in self.model.T)
        self.model.cost = Objective(rule=cost_rule)
        
        
        # Local power constraint
        def local_power_rule (model, i):
            return self.model.xPlus[i] - self.model.xMinus[i] == self.model.xGrid[i]
        self.model.local_power = Constraint(self.model.T, rule=local_power_rule)
        # Local energy balance constraint
        def local_balance_rule (model, i):
            return self.model.etab*(self.model.bSoC[i] - self.model.bSoC[i-self.model.delta]) + self.model.demP[i] - self.model.genP[i] == self.model.xGrid[i]
        self.model.local_balance = Constraint(self.model.T2, rule=local_balance_rule)
        # Local battery charging constraints
        def bLower_rule (model, i):
            return self.model.bSoC[i] - self.model.bSoC[i-self.model.delta] >= - self.model.bmin
        self.model.bLower = Constraint(self.model.T2, rule=bLower_rule)
        def bUpper_rule (model, i):
            return self.model.bSoC[i] - self.model.bSoC[i-self.model.delta] <= self.model.bmax
        self.model.bUpper = Constraint(self.model.T2, rule=bUpper_rule)
        self.k=[0, 23.5]
        def StartEndSoC_rule (model, i):
            return (self.model.bSoC[i] == self.model.soc0)
        self.model.StartEndSoC = Constraint(self.k, rule=StartEndSoC_rule)

    def solve(self):
        solver = pyomo.opt.SolverFactory('ipopt')
        results = solver.solve(self.model, tee=True)
        
        if (results.solver.status != pyomo.opt.SolverStatus.ok):
            logging.warning('Check solver not ok?')
        if (results.solver.termination_condition != pyomo.opt.TerminationCondition.optimal):  
            logging.warning('Check solver optimality?') 
        
    def printing(self):
        ### Prints results whilst running 
        print('\nEnergy import: ') 
        for i in self.model.xGrid:
            print ("   ", i, value(self.model.xGrid[i]))
        print('\nBattery State of Charge: ') 
        for i in self.model.xGrid:
            print ("   ", i, value(self.model.bSoC[i]))
         
    def exportresults(self):
        ### Write results to CSV file
        raw_data = []
        labels = {'t', 'xGrid', 'bSoC'}
        df1 = pd.DataFrame(raw_data, columns = labels)
        """Iteratively appending rows to a DataFrame can be more computationally 
        intensive than a single concatenate. A better solution is to append those 
        rows to a list and then concatenate the list with the original DataFrame 
        all at once."""
        for i in self.model.xGrid:
            # Circles through all indexes and adds variables' results into a list
            partial_values = [i,value(self.model.xGrid[i]), value(self.model.bSoC[i])]
            # Appends partial values using a dictionary, with labels as columns
            raw_data.append(dict(zip(labels,partial_values)))
        # Appends all raw data into a new data frame
        df_output = df1.append(raw_data)
        # Writes to CSV file
        df_output.to_csv('/media/daniel/HDDfiles/Projects/CommProject/PythonImplementation/BatteryModel/Result_Test.csv')
            
if __name__ == '__main__':
        solveprob = WIP('/media/daniel/HDDfiles/Projects/CommProject/PythonImplementation/BatteryModel/2216.csv')
        solveprob.solve()
        #solveprob.printing()
        #solveprob.exportresults()
        print('\n\n------------')
        print('Success! \nCost: ', solveprob.model.cost())
        
        """ Print variables, somehow! """
        print('\nEnergy import on t=23.5: ', value(solveprob.model.xGrid[23.5]))
        #print('\nBattery State of Charge: ', solveprob.model.bSoC())
