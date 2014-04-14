S4FOLDER = "D:/Dropbox/Theorie/grattings/RCWA/S4/"

import sys
import os.path as osp
import os
import numpy as np
import pylab
import shutil
import glob
from matplotlib.mlab import griddata
import json
import StringIO

def load_eps(name):
    table = np.loadtxt(name)
    return table[:,2].reshape((table[:,0].max()+1,table[:,1].max()+1))

def load_data(name):
    """
    name should be the path to a filename *.dat, containing
    first line: a json with some metadata:
        required keys: 
            -"x": the name of the x axis
            -"y": the name of the y axis
            -"z": the name of the data
    rest of the file: data in space separated format
        even lines: values of x
        odd lines: values of y
    the array is not necessarily squared or evenly spaced
    """
    
    name = osp.split(name)[-1]
    (data_file,
     lambda_file,
     thickness_file,
     image_file) = get_names(name)
    meta = {}
    first = True
    with open(S4FOLDER + "data/" + data_file, 'r') as f:
        line_json = f.readline()
        meta = json.loads(line_json)
        x = []
        y = []
        z = []
        line = f.readline()
        while(line != ""):
            s = StringIO.StringIO(line)
            ### read line of x values
            even_line = np.loadtxt(s)
            y_value = even_line[0]
            x_values = even_line[1:]
            ### read line of z values
            line = f.readline()
            s = StringIO.StringIO(line)
            odd_line = np.loadtxt(s)
            assert(odd_line[0]==y_value)
            z_values = odd_line[1:]
            ### appends data to tables
            x.append(x_values)
            z.append(z_values)
            y.append(y_value)
            ### next line
            line = f.readline()   
    y = np.array(y)
    return DataResult(x, y, z, meta)

def load_last():
    """
    load the lattest subscript file in the folder data.
    """
    list_names = glob.glob(S4FOLDER + "data/????_*.dat")
    list_names.sort()
    last = list_names[-1]
    print "loading " + last
    return load_data(last)

class DataResult:
    """
    Object containing the data from a simulation 
      *self.raw_x is a list of 1d array containing x-values for each slice 
       (lambdas)
      *self.raw_y is a 1d array containing the y-value of each slice 
       (thicknesses)
      *self.raw_z is a list of 1d array containing the z-values for each 
       slice (reflectivity)
      *self.meta contains the meta data as stored in the json (first line of 
       .dat file)
    """
    
    def __init__(self, raw_x, raw_y, raw_z, meta):
        self.raw_x = raw_x
        self.raw_y = raw_y
        self.raw_z = raw_z
        self.meta = meta
    
    def interp_data(self, n_points):
        """
        returns a squared table of data with x-values evenly spaced
        """

        x_new = np.linspace(self.raw_x[0][0], self.raw_x[0][-1], n_points)
        z_new = []
        for x, z in zip(self.raw_x, self.raw_z):
            y_slice = np.interp(x_new, x, z)
            z_new.append(y_slice)
        z_new = np.array(z_new)
        return z_new
        
        
    def plot_image(self, n_points_x=1000):
        """
        Creates a colorplot image (new figure) of the z-data as a function of
        x and y
        
        Since raw data are not necessarily square arrays, the data can be interpolated 
        along the x axis to make the array square...
        
        If n_points_x is set to 0, then, the raw_data are used, beware, the data
        need to be squared and evenly spaced in this case.
        """
        
        if n_points_x==0:
            data_interp = np.array(self.raw_z)
            assert(len(np.shape(data_interp==2)))
        else:
            data_interp = self.interp_data(n_points_x)
        pylab.figure()
        pylab.imshow(data_interp,
                     cmap=pylab.cm.Reds,
                     interpolation='none',
                     aspect='auto',
                     origin='lower',
                     extent=[self.raw_x[0][0], 
                             self.raw_x[0][-1],
                             self.raw_y[0],
                             self.raw_y[-1]])
        try:
            pylab.xlabel(self.meta["x"])
            pylab.ylabel(self.meta["y"])
        except KeyError:
            pass
        cb = pylab.colorbar()
        try:
            cb.set_label(self.meta["z"])
        except KeyError:
            pass
        
    def plot_slice(self, i_slice=0):
        """
        plot the slice for the i^th value of y
        """
        
        pylab.plot(self.raw_x[i_slice], self.raw_z[i_slice])

    def cascaded_slices(self, style=None, i_slice_start=0, i_slice_stop=-1, by_n=1):
        """
        plot the slices one over each others for y values between 
        index i_slice_start and i_slice_stop, every by_n
        """
        pylab.figure()
        for index,(x, y) in enumerate(zip(self.raw_x, self.raw_z)[i_slice_start:i_slice_stop:by_n]):
            if style is not None:
                pylab.plot(x, y + index, style)
            else:
                pylab.plot(x, y + index)
        
def get_names(name):
    file_name_base = osp.splitext(name)[0]
    data_file = file_name_base + ".dat"
    lambda_file = file_name_base + ".dat.lambdas"
    thickness_file = file_name_base + ".dat.thicknesses"
    image_file = file_name_base + ".jpg"
    
    return (data_file,
            lambda_file,
            thickness_file,
            image_file)

if __name__=="__main__":
    """backup_result(sys.argv[1])"""
    with open("file_list.txt", 'r') as f:
        l = f.readline()
        while(l!=""):
            filename = l
            l = f.readline()
    plot_result(filename)