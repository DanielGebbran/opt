#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 13:28:34 2019
TO RUN: GO TO FOLDER, RIGHT CLICK: OPEN IN TERMINAL,TYPE:
    pyomo solve --solver=ipopt BatterySelfContainedAbstractModel.py
    
    Result must yield 
    Function Value: 0.18432001722987917
    
    Relevant data is on file: "Test_Reduced_9_periods.dat"
@author: daniel
"""

from pyomo.environ import *
import pandas as pd
#import numpy as np

model = AbstractModel()


# Reading CSV files
consumer_file = pd.read_csv('/media/daniel/HDDfiles/Projects/CommProject/PythonImplementation/BatteryModel/BatFlt.csv')
consumer_file.columns = consumer_file.columns.str.strip() #Removes spaces from header
# Defining index for sets
consumer_file.set_index('T',inplace=True) #Performs indexing of column 'T' in place, i.e. on the run
# Defining data for sets
T_set = consumer_file.index.unique()

# Timing sets and parameters
model.T = Set(initialize=T_set)
model.T2 = Set(initialize = model.T - [0])
#model.T2 = Set(initialize= [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]) 
# used with time = k+1, previous updates, not battery initial SoC. Set operation of subtraction used to declare
#model.T = Set()
model.t0     = Param(default=0.0)
model.tend   = Param(initialize=4.5)
model.delta  = Param(default=0.5)

# Testing, printing:
# currently performed inside another definition!

# Cost parameters
def init_c0(model,i):
    return 0
model.c2     = Param(model.T, initialize = init_c0)
#model.c2     = Param(model.T, initialize = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
#model.c1     = Param(model.T, initialize = [0.12, 0.12, 0.22, 0.22, 0.52, 0.52, 0.22, 0.22, 0.12, 0.12] )
#[0.12, 0.12, 0.22, 0.22, 0.52, 0.52, 0.22, 0.22, 0.12, 0.12]
def init_c1(model,i):
    if i == 0.5 or i == 1 or i == 4 or i == 4.5:
        return 0.12
    elif i == 2.5 or i == 3:
        #model.T.pprint()
        #model.T2.pprint()
        return 0.52
    else:
        return 0.22
model.c1     = Param(model.T, initialize = init_c1)
#model.c0     = Param(model.T, initialize = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
model.c0     = Param(model.T, initialize = init_c0)

# Local demand and generation inputs
# read a CSV, implement a def/return for genP reading the CSV dataframe, read directly from CSV
#model.genP   = Param(model.T)


def init_demP(model,j):
    #return consumer_file.ix[j, 'demP        ']
    return consumer_file.loc[j, 'demP']
def init_genP(model,i):
    return consumer_file.ix[i, 'genP']

model.genP   = Param(model.T, initialize = init_genP)
model.demP   = Param(model.T, initialize = init_demP)
#model.genQ
#model.demQ

# Battery parameters
model.bmin   = Param(initialize=1.75)
model.bmax   = Param(initialize=1.75)
model.cmin   = Param(initialize=0)
model.cmax   = Param(initialize=7.5)
model.soc0   = Param(initialize=3)
model.etab   = Param(initialize=0.92)

# Decision variables
model.xPlus     = Var(model.T, within=NonNegativeReals)
model.xMinus    = Var(model.T, within=NonNegativeReals)
model.xGrid     = Var(model.T)
model.bSoC      = Var(model.T, bounds=(model.cmin,model.cmax))


# Minimize import cost of household
def cost_rule(model):
    return sum((((model.xPlus[i])**2)*(model.c2[i]) + model.c1[i]*model.xPlus[i] + model.c0[i]) for i in model.T)
model.cost = Objective(rule=cost_rule)


# Local power constraint
def local_power_rule (model, i):
    return model.xPlus[i] - model.xMinus[i] == model.xGrid[i]
model.local_power = Constraint(model.T, rule=local_power_rule)
# Local energy balance constraint
def local_balance_rule (model, i):
    return model.etab*(model.bSoC[i] - model.bSoC[i-model.delta]) + model.demP[i] - model.genP[i] == model.xGrid[i]
model.local_balance = Constraint(model.T2, rule=local_balance_rule)
# Local battery charging constraints
def bLower_rule (model, i):
    return model.bSoC[i] - model.bSoC[i-model.delta] >= - model.bmin
model.bLower = Constraint(model.T2, rule=bLower_rule)
def bUpper_rule (model, i):
    return model.bSoC[i] - model.bSoC[i-model.delta] <= model.bmax
model.bUpper = Constraint(model.T2, rule=bUpper_rule)
k=[0, 4.5]
def StartEndSoC_rule (model, i):
    return (model.bSoC[i] == model.soc0)
model.StartEndSoC = Constraint(k, rule=StartEndSoC_rule)

# Above is equivalent to:
#def EndSoC_rule (model):
#    return model.bSoC[model.tend] == model.soc0
#model.EndSoC = Constraint(rule=EndSoC_rule)
#def startSoC_rule (model):
#    return model.bSoC[model.t0] == model.soc0
#model.startSoC = Constraint(rule=startSoC_rule)

#### Not successful implementing the following as set declaration:
#def T2_init(model):
#    k = model.t0
#    t2_list = [model.t0]
#    while k < model.tend:
#        k += model.delta
#        t2_list.append(k)
#    print (t2_list)
#    return  t2_list
#model.T2 = Set(initialize=T2_init) # used with time = k+1, previous updates, not battery initial SoC
#
#def T_init(model):
#    k = model.t0
#    t1_list = [model.delta+model.t0]
#    while k < model.tend:
#        k += model.delta
#        t1_list.append(k)
#    print (t1_list)
#    return  t1_list
#model.T = Set(initialize=T_init)



