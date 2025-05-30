import numpy as np
import matplotlib.pyplot as plt
import csv
from pathlib import Path

csvfilename = input("Input the name of the .csv file (the .csv will automatically be appended.)")
csvfilename += ".csv"
fileloc = Path(__file__).parent
synthdata = fileloc / csvfilename #would benefit from a prompt to input a file, or draw from the most recent one. currently this assumes the py file is in the same directory as the final code.
t = []
x = [] #personally prefer a list over an array here since this can handle any # of points

with open(synthdata, mode='r') as synth:
    iterator = csv.reader(synth)
    next(iterator)
    for row in iterator:
        try:
            t.append(float(row[1]))
        except:
            pass
        try:
            x.append(float(row[0]))#get data from csv
        except:
            pass
        
def cmp(x,t):
    newx = np.zeros((len(x), 2))
    newt = np.zeros(len(t)) #converts standard lists to numpy arrays
    if len(x) != len(t):
        raise IndexError("Length of arrays x and t are not identical, and are (respectively)", len(x), "and", len(t))
    for i in range(len(x)):
        newx[i] = [1,x[i]**2]
        newt[i] = (t[i]/2)**2
    v = np.linalg.lstsq(newx,newt)[0][1]
    relperm = v*((3e8)**2) #v is already of the form 1/v^2, so just multiplying it by speed of light squared works 
    return t[0], float(relperm)
#try:
    #print("Zero offset time is", cmp(x,t)[0], "and the relative permittivity is", cmp(x,t)[1])
#except IndexError:
    #print("Index Error - this was likely caused by the x and t arrays being different lengths.")
    #print("Length of x:", len(x), ", length of t:", len(t))
#except NameError:
    #print("Name Error - one or more arrays was ill-defined/referenced. (this shouldn't happen?)")
#except:
    #print("Some other error.") || alternate error check method