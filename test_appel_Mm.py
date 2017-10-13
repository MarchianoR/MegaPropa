import sys
sys.path.append('../mm')
import megaSysteme_128 as mega
import numpy as np
import threading
import time
import pyqtgraph as pg
import pylab as plt
import datetime
import signal
import pyqtgraph.multiprocess as mp

# permet d interrompre le mode interactif avec un CTRL+C
def signal_handler(signal, frame):
    print 'You pressed Ctrl+C!'
    print 'Lavu is stopped'
    Mm.stop()
# Init Affichage

pg.mkQApp()
# Create remote process with a plot window

proc = mp.QtProcess()
rpg = proc._import('pyqtgraph')



list_res = []
list_time = []

def processing(Mm):
    global curve, MicStateWin
    
    
    i = 0
    nb_acqui = 0
    while(Mm.num_pkt < Mm.n_pkt and Mm.last_pkt==0):
    
        res, data = Mm.get_data(duree=0.1)

        if res==1:
            print("Acquisition en cours",nb_acqui)
            
            nb_acqui = nb_acqui + 1
            cpt = data[:,2].copy()
            curve.setData(y=cpt, _callSync='off')
           
        else:
            
            pass
        i = i + 1
   


plotwin = rpg.plot()
curve = plotwin.plot(pen='y')

mems = np.zeros((16, 8), np.bool)
mems[0:2,:] = 1
signal.signal(signal.SIGINT, signal_handler)
Mm = mega.System128(duree=50., mems=mems, va=np.zeros((4,), np.bool), cpt=1, interactif=1, verbose=0)
t = threading.Thread(target=processing, args=(Mm,))

print(Mm)

Mm.start()
t.start()
Mm.show()
Mm.close()
 
sys.exit()
