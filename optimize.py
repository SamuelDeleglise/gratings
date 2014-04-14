from plot_result import load_last, load_eps, S4FOLDER


from collections import OrderedDict
import json
import subprocess
from numpy import linspace, amax
from scipy.optimize import minimize
import shutil
import pylab
import os.path as osp
import os
import gc

from scipy.interpolate import splrep, sproot, splev

N_CALLS = 0

class MultiplePeaks(Exception): pass
class NoPeaksFound(Exception): pass

def above_threshold(x, y, k=10, threshold=0.99):
    """
    Determine the "width above the threshold"
    
    The function uses a spline interpolation of order k.
    """

    half_max = amax(y)/2.0
    s = splrep(x, y - threshold)
    roots = sproot(s)
    if len(roots)==0:
        interv = [(x[0], x[-1])]
    else:
        interv = [(x[0],roots[0])]
        for r in roots[1:]:
            interv.append((interv[-1][-1], r))
        interv.append((interv[-1][-1], x[-1]))
    
    tot = 0
    len_max = 0
    for start, stop in interv:
        if(splev((start+stop)/2, s)>0):
            tot += stop - start
            if stop-start>len_max:
                len_max = stop-start
    pylab.figure("reflexion")
    xx = linspace(x[0],x[-1],1000)
    yy = splev(xx, s) + threshold
    pylab.plot(xx,yy)
    pylab.plot(x,y)    
    return len_max

def calculate(filename, **kwds):
    """
    sets params.json to kwds and runs S4 with the .lua file filename. 
    """
    
    with open(S4FOLDER + "params.json","w") as f:
        json.dump(kwds, f)
    print subprocess.call([S4FOLDER + "S4.exe", filename], shell=True)


class HtmlLogger(object):
    luafile = ""#to be set in the derived class
    
    static_params = {}
    variables = OrderedDict()#to be set in the derived class
    data_folder = "." #to be set in the derived class
    threshold = 0.9    
    
    def append_iteration_to_report(self, res):
        shutil.move(S4FOLDER + res.meta["data_filename"], self.data_folder)
        shutil.move(S4FOLDER + res.meta["data_filename"] + '.pov', self.data_folder)
        shutil.move(S4FOLDER + res.meta["data_filename"] + '.eps', self.data_folder)
        fig = pylab.figure("reflexion")
        res.plot_slice()
        figpath = self.data_folder + "/" + osp.split(res.meta["data_filename"])[-1] + ".jpg"
        fig.savefig(figpath)
        pylab.close(fig)
        
        eps_prof = load_eps(self.data_folder+ "/" + osp.split(res.meta["data_filename"])[-1] + ".eps")
        figepspath = self.data_folder +"/"+ osp.split(res.meta["data_filename"])[-1] + "_eps.jpg"
        fig = pylab.imshow(eps_prof, extent=(-res.meta["Lambda_x"]/2,
                                       res.meta["Lambda_x"]/2,
                                       -res.meta["Lambda_y"]/2,
                                       res.meta["Lambda_y"]/2),
                                       aspect='equal').figure
        pylab.colorbar()
                                      
        fig.savefig(figepspath)
        pylab.close(fig)
        
        self.add_line_to_html(res, figpath, figepspath)
        return figpath
    
    def add_line_to_html(self, res, figpath, figepspath):
        self.html_file.write("""<TR>""")
        for val in self.variables.values():
            self.html_file.write("<TD>" + str(val) + "</TD>")
        self.html_file.write("""<TD> <a href="#" data-chart=\"""" + \
                             osp.split(figpath)[-2] + "/" + osp.split(figpath)[-1] +\
                              """\"> Click me </a> </TD>""")
        
        self.html_file.write("<TD>" + str(res.meta["width_of_plateau"]) + "</TD>")
        
        self.html_file.write("""<TD> <a href=\"#\" data-chart=\""""+ osp.split(figpath)[-2] + "/"+ osp.split(figepspath)[-1] + """\"> Click me </a></TD>""")
        self.html_file.write("<TD>" + osp.split(res.meta["data_filename"])[-2]+"/"+osp.split(res.meta["data_filename"])[-1] + "</TD></TR>\n")
        self.html_file.flush()
    
    def prepare_html(self):
        self.html_file_name = self.data_folder + '.html'
        self.html_file = open(self.html_file_name, 'w')
        #"http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"
        self.html_file.write("""<HEAD>
<link rel="stylesheet" type="text/css" href="optimize.css" media="screen" />
<script src="jquery.min.js"></script> 
<script type="text/javascript">
$(document).ready(function(e) {
    $('a[data-chart]').click(function(e) {
        $("#chart").html('<img src="'+$(this).data('chart')+'">');
        e.preventDefault();
    });
});
</script>
</HEAD>

<div id="chart"></div>

""")
        
        self.html_file.write("""<TABLE BORDER="1"> 
          <CAPTION> constant parameters </CAPTION> 
          <TR>""")
        for k in self.static_params.keys():
            self.html_file.write("<TH> " + k + "</TH>\n")
        self.html_file.write("<TR>")
        for v in self.static_params.values():
            self.html_file.write("<TD>" + str(v)+ "</TD>") 
        self.html_file.write("</TABLE>\n")
    
        self.html_file.write("""
<TABLE BORDER="1"> 
  <CAPTION> variable parameters for optimization </CAPTION> 
  <TR>""")
        for k in self.variables.keys():
            self.html_file.write("<TH> " + k + "</TH>\n") 
        self.html_file.write("<TH> image </TH>\n") 
        self.html_file.write("<TH> width(r>" + str(self.threshold) + "%)[nm] </TH>")
        self.html_file.write("<TH> eps profile </TH>") 
        self.html_file.write("<TH> data file </TH>\n</TR>") 

    def func(self, var):
#        global N_CALLS
#        N_CALLS+=1
#        if N_CALLS == 10:
        gc.collect()
#            N_CALLS = 0

        for k,v in zip(self.variables.keys(), var):
            v = self.constrain_param(k, v)
            self.variables[k] = v
        params = self.variables.copy()
        params.update(self.static_params)
        params["is_2d"] = False
        print params
        calculate(self.luafile, **params)
        res = load_last()
        self.res = res
        res.meta["width_of_plateau"] = self.width_of_plateau()
        self.append_iteration_to_report(res)
        return -res.meta["width_of_plateau"]
    
    def width_of_plateau(self):
        """n_points = 30000
        x_start = self.res.raw_x[0][0]
        x_stop  = self.res.raw_x[0][-1]
        x_tot = x_stop - x_start
        y = self.res.interp_data(n_points)[0]"""
        try:
            ret = 1000*above_threshold(self.res.raw_x[0], self.res.raw_z[0], threshold=self.threshold)
            
        except NoPeaksFound:
            ret = 0
        return ret
#        return 1000*len(y[y>self.threshold])*x_tot/n_points


class Optimize(HtmlLogger):
    """
    Creates an optimizer
    """
    
    def make_2d_image(self):
        params = self.variables.copy()
        params.update(self.static_params)
        params["is_2d"] = True
        print params
        calculate(self.luafile, **params)
        r = load_last()
        r.plot_image()
    
    def make_new_data_folder(self, name):
        num = 0
        for p in os.listdir(self.summary_folder):
            if os.path.isdir(self.summary_folder + '/' + p):
                try:
                    num = max(num, int(p[:4]))
                except ValueError:
                    pass
        name = "%04i_"%(num+1) + name
        os.mkdir(name)
        self.data_folder = name
        return name
    
    def constrain_param(self, par_name, val):
        try:
            min_val, max_val = self.constraints[par_name]
        except KeyError:
            return val
        if val<min_val:
            return min_val
        if val>max_val:
            return max_val
        return val
    
    def scan(self, par_name, min, max, n_steps):
        self.make_new_data_folder(name="scan_" + par_name)
        self.prepare_html()
        for val in linspace(min, max, n_steps):
            self.variables[par_name] = val
            self.func(self.variables.values())
        self.html_file.write("</TABLE>")
        print "making 2D image"
        self.make_2d_image()
        fig = pylab.gcf()
        figpath = self.data_folder + "/" + osp.split(self.res.meta["data_filename"])[-1] + "_2d.jpg"
        fig.savefig(figpath)
        self.html_file.write("<IMG SRC=\"" + figpath+ "\"ALT=\"here should be a 2d image\" WIDTH=600 HEIGHT=600>\n")
        self.html_file.close()
    
    def optimize(self, name="optimize", maxiter=100):
        self.make_new_data_folder(name)
        self.prepare_html()
        ret = minimize(self.func, self.variables.values(), method="Nelder-Mead", options={'maxiter':maxiter})
        self.html_file.write("</TABLE>")
        print "making 2D image"
        self.make_2d_image()
        fig = pylab.gcf()
        figpath = self.data_folder + "/" + osp.split(self.res.meta["data_filename"])[-1] + "_2d.jpg"
        fig.savefig(figpath)
        self.html_file.write("<IMG SRC=\"" + figpath+ "\"ALT=\"here should be a 2d image\" WIDTH=600 HEIGHT=600>\n")
        self.html_file.close()
    
