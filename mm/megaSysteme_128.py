# -*- coding: utf-8 -*-
from __future__ import division
import megaSysteme_core as core
import libusb1
import numpy as np
import time
import ctypes
import sys

if sys.version_info > (3,):
    long = int

class version():
    def __init__(self):
        self.version = 1

class System128(core.MegaMicros):
    def __init__(self, duree=0.00, filename='toto.dat', path='.',
                 mems=np.ones((16, 8), np.bool), va=np.ones((4), np.bool), cpt=1,
                 clockdiv=9, interactif=0, verbose=0):

        core.MegaMicros.__init__(self, duree=duree, filename=filename, path=path,
                 mems=mems, va=va, cpt=cpt,
                 clockdiv=clockdiv, interactif=interactif, verbose=verbose, addr=0x82)

        self.usbh = core.usb2(my_vid=0xFE27, my_pid=0xAC00)
        self.init_module128()
        self.init_transfert_usb()
        self.version = 128
        self.lavu= 1


    def init_module128(self):
        """
        initialisation du boitier Megamicros
        :param handle: usb device handle [objet port usb']
        :return:
        """
        # --------------------------------
        # Initialisation carte
        # --------------------------------
        print("initialisation de la carte Mm")
        buf = ctypes.create_string_buffer(16)

        # reset acq128	et purge fifo
        buf[0] = b'\x00'  # commande Reset
        self.usbh.write_command(0xB0, buf, 1)
        buf[0] = b'\x06'  # commande Purge Fifo
        self.usbh.write_command(0xB0, buf, 1)

        # reset fx2 et purge fifo
        self.usbh.write_command(0xC0, buf, 0)
        self.usbh.write_command(0xC2, buf, 0)

        # init acq128 (clockdiv)
        buf[0] = b'\x01'  # commande init
        buf[1] = b'\x09'  # clockdiv=9
        self.usbh.write_command(0xB1, buf, 2)

        # attente
        time.sleep(1)  # nécessaire pour que les MEMS soient bien démarrés...

        # Nombre de tixels à acquérir (COUNT )
        c = long(self.COUNT)
        buf[0] = b'\x04'  # commande COUNT
        buf[1] = chr(c & 0x000000ff)
        buf[2] = chr((c & 0x0000ff00) >> 8)
        buf[3] = chr((c & 0x00ff0000) >> 16)
        buf[4] = chr((c & 0xff000000) >> 24)
        self.usbh.write_command(0xB4, buf, 5)

        # Choix DataType
        buf[0] = b'\x09'
        if self.datatype == "int32":
            buf[1] = b'\x00'  # 00:int32,  01:float32
        elif self.datatype == "float32":
            buf[1] = b'\x01'  # 00:int32,  01:float32
        self.usbh.write_command(0xB1, buf, 2)

        # initialisation des voies
        self.SelectChannels()
        page_txt = [b'\x00', b'\x01', b'\x02', b'\x03', b'\x04', b'\x05', b'\x06', b'\x07', b'\x08', b'\x09', b'\x0A',
                    b'\x0B', b'\x0C', b'\x0D', b'\x0E', b'\x0F', b'\xFF']
        for i in range(len(page_txt)):
            buf[0] = b'\x05'  # commande active
            buf[1] = b'\x00'  # module
            buf[2] = page_txt[i]  # Page
            buf[3] = self.page[i]  # micros actifs
            # print str(struct.unpack('B',self.page[i]))
            self.usbh.write_command(0xB3, buf, 4)

        print("initialisation de la carte Mm .................. ok")

    def reset_fifo(self):
        # reset FIFOs
        msg = b'\x00'
        self.usbh.write_command(0xB0, msg, 1)
        msg = b'\x06'
        self.usbh.write_command(0xB0, msg, 1)
        self.usbh.write_command(0xC0, msg, 0)
        self.usbh.write_command(0xC2, msg, 0)

    def start(self):
        # start
        msg = b'\x02' + b'\x00'  # commande start + trig soft
        self.usbh.write_command(0xB1, msg, 2)

    def close(self):
        if self.filename and self.interactif == 0:
            self.Filep.close()
        for i in range(self.n_tdf):
            libusb1.libusb_free_transfer(self.transfert[i])
        self.reset_fifo()
        time.sleep(1)
        self.usbh.close()

if __name__ == '__main__':
    mems = np.zeros((16, 8), np.bool)
    mems[0:4, :] = 1
    Mm = System128(duree=3., mems=mems, va=np.zeros((4,), np.bool), cpt=1)
    Mm.start()
    Mm.show()
    print(Mm)
    Mm.close()