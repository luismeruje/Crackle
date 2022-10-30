import serial
import numpy as np
import matplotlib.pyplot as plt
import time, math
import sys
from matplotlib.widgets import Button
from scipy.optimize import curve_fit
from scipy.interpolate import Akima1DInterpolator, CubicSpline, UnivariateSpline, lagrange
import configparser

config = configparser.ConfigParser()
config.read(sys.argv[1])



#Temps in C, time in seconds
drying = int(config['DEFAULT']['DryingTime'])
drying_temp = int(config['DEFAULT']['DryingTemp']) #(always up from here)

first_crack = int(config['DEFAULT']['FirstCrackTime']) + drying
first_crack_temp = int(config['DEFAULT']['FirstCrackTemp'])

finish = int(config['DEFAULT']['FinishTime']) + first_crack 
target_temp = int(config['DEFAULT']['FinishTemp'])

max_x = finish + 10

#Logic: Fast as possible to 93C, 4 to 5 minutes to 150C, 4 to 5 more minutes to first crack, 2 to 4 minutes to end.
ref_x = [0, 5, 10, 35, drying, first_crack ,finish]
ref_y = [170, 100, 65, 93, drying_temp, first_crack_temp, target_temp]


def binomial_function(x,a,b,c):
    return a * np.power(x,2) + b * x + c

def log_function(x,a,b):
    
    return a * np.log(x) + b  

def fivepl(x, a, b, c, d, g):
    return ( ( (a-d) / ( (1+( (x/c)** b )) **g) ) + d )
class RoastingManager():


    def __init__(self, ax):
        self.ser = serial.Serial(config['DEFAULT']['SerialPort'])
        self.ax = ax
	
	#Chargin curve
        popt_binomial, _ = curve_fit(binomial_function, ref_x[:4], ref_y[:4])
        a,b,c = popt_binomial
        self.ref_x_smooth = np.arange(0, 35, 1,dtype='float32')
        self.ref_y_smooth = binomial_function(self.ref_x_smooth,a,b,c)
	
	#Drying curve
        popt_log, _ =curve_fit(log_function,ref_x[3:5], ref_y[3:5], maxfev=15000)
        a,b= popt_log
        x_2 = np.arange(ref_x[3],ref_x[4],dtype='float32')
        self.ref_x_smooth = np.append(self.ref_x_smooth, x_2)
        self.ref_y_smooth = np.append(self.ref_y_smooth, log_function(x_2,a,b))
	
        #Yellow to first crack curve
        popt_log, _ =curve_fit(log_function,ref_x[4:6], ref_y[4:6], maxfev=15000)
        a,b= popt_log
        x_2 = np.arange(ref_x[4],ref_x[5],dtype='float32')
        self.ref_x_smooth = np.append(self.ref_x_smooth, x_2)
        self.ref_y_smooth = np.append(self.ref_y_smooth, log_function(x_2,a,b))

        #First crack to finish curve
        popt_log, _ =curve_fit(log_function,ref_x[4:], ref_y[4:], maxfev=15000)
        a,b= popt_log
        x_2 = np.arange(ref_x[5],max_x,dtype='float32')
        self.ref_x_smooth = np.append(self.ref_x_smooth, x_2)
        self.ref_y_smooth = np.append(self.ref_y_smooth, log_function(x_2,a,b))

        self.tempText = plt.gcf().text(0.06, 0.92, 'Temp: NaN ºC', fontsize=14, color='red')
        self.timeText = plt.gcf().text(0.29, 0.92, 'Time: 00:00', fontsize=14, color='blue')

    def resetFigure(self, event):
        self.ax.clear()
        self.ax.axhspan(0,93,0,max_x,facecolor='green',alpha=0.5)
        self.ax.axhspan(drying_temp,first_crack_temp,0,max_x,facecolor='yellow',alpha=0.5)
        self.ax.axhspan(first_crack_temp,target_temp,0,max_x,facecolor='red',alpha=0.5)
        self.ax.plot(self.ref_x_smooth, self.ref_y_smooth)
        self.ax.axvline(drying)
        self.ax.axvline(first_crack)
        self.ax.axvline(finish)
	#self.ax.plot(self.ref_x_smooth, self.y_target)
        #self.ax.plot(self.ref_x_smooth, self.y_drying)
        #self.ax.plot(self.ref_x_smooth, self.y_first_crack)

        self.beginTime = time.time()
        self.timeText.set_text('Time: 00:00')

    def measureTemps(self):
        for i in range(5000):
            try:
                elapsed = time.time() - self.beginTime
                self.ser.reset_input_buffer()
                temp = self.ser.readline()
                #print(temp)
                temp = ''.join(filter(str.isdigit, str(temp)))
                if(int(temp) < 1000):
                    self.ax.scatter(elapsed, int(temp))
                    self.tempText.set_text('Temp: ' + str(temp) + ' ºC')
                self.timeText.set_text('Time: ' + '{:02d}'.format(int(elapsed/60)) + ':' + '{:02d}'.format(int(elapsed%60)))
                plt.pause(0.005)
            except Exception as e: 
                print(e)

    def quit(self, event):
        plt.close()
        sys.exit(0)
ax1 = None
fig = plt.figure()
ax1 = fig.add_subplot(111)
axReset = plt.axes([0.70, 0.90, 0.1, 0.075])
axClose = plt.axes([0.85, 0.90, 0.1, 0.075])

manager = RoastingManager(ax1)
manager.resetFigure(None)
resetButton = Button(axReset, 'Reset')
resetButton.on_clicked(manager.resetFigure)
quitButton = Button(axClose, 'Close')
quitButton.on_clicked(manager.quit)
manager.measureTemps()

plt.show()
