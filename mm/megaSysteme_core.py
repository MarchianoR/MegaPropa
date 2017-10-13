# -*- coding: utf-8 -*-
"""
Modules de gestion d'acquisition avec Megamicros.

Pour avoir les droits read/write sur le système d'acquisition:

1) sudo gedit /etc/udev/rules.d/USBdev-Megamicros.rules

2) copier-coller:
    - Pour Ubuntu 12.04 :

SUBSYSTEM!="usb_device", ACTION!="add", GOTO="USBdev-Megamicros_rules_end"
SYSFS{idVendor}=="fe27", SYSFS{idProduct}=="ac00", GROUP="users", MODE="0666"
LABEL="USBdev-Megamicros_rules_end"

    - Pour Ubuntu 14.04

SUBSYSTEM=="usb", ATTRS{idVendor}=="fe27", ATTRS{idProduct}=="ac00", MODE="0666"

3) sudo udevadm trigger (pour reloader les rules)
"""
from __future__ import division
import libusb1
import numpy as np
import time
import ctypes
import struct
import sys

NULL = None

if sys.version_info > (3,):
    long = int

class usb():
    """
    Class générique contenant les commandes de gestion de l'USB
    """

    def __init__(self, my_vid=0xFE27, my_pid=0xAC00):
        self.my_vid = my_vid
        self.my_pid = my_pid
        self.initialisation()
        self.LIBUSB_RECIPIENT_DEVICE = 0x00
        self.LIBUSB_REQUEST_TYPE_VENDOR = 0x02 << 5
        self.LIBUSB_ENDPOINT_OUT = 0x00
        self.LIBUSB_TRANSFER_TIMED_OUT = 2
        self.TIMEOUT = 1000

    def initialisation(self):
        """
        initialisation de la liaison usb

        :return: un handle sur la liaison usb (self.handle)
        """
        print('Initialisation usb')
        libusb1.libusb_init(NULL)
        libusb1.libusb_set_debug(NULL, 3)
        self.handle = libusb1.libusb_open_device_with_vid_pid(NULL, self.my_vid, self.my_pid)
        libusb1.libusb_claim_interface(self.handle, 0)
        print('Initialisation usb  ........  ok')

    def close(self):
        """
        fermeture de la liaison usb

        :return:
        """
        print ('* fermeture de la liaison usb *')
        libusb1.libusb_release_interface(self.handle, 0)
        libusb1.libusb_close(self.handle)
        libusb1.libusb_exit(NULL)
        print ('* liaison usb fermee  *')


class usb2(usb):
    """ classe concue pour la gestion de l'usb2
    """

    def __init__(self, my_vid=0xFE27, my_pid=0xAC00):
        usb.__init__(self, my_vid=my_vid, my_pid=my_pid)
        self.version = 2
        print ("liaison par USB2")

    def write_command(self, request, data_ptr, length):
        """
        fonction qui envoie une commande de controle vers USB2

        :param request: signature du commande controle
        :param data_ptr: data du commande controle
        :param length: taille de data_ptr
        :return:
        """
        typerequest = self.LIBUSB_RECIPIENT_DEVICE | self.LIBUSB_REQUEST_TYPE_VENDOR | self.LIBUSB_ENDPOINT_OUT
        value = 0
        index = 0
        if (length == 0):
            dat = '\x00'
            dbg = libusb1.libusb_control_transfer(self.handle, typerequest, request, value, index, dat, 1, self.TIMEOUT)
            assert dbg == 1
        else:
            dbg = libusb1.libusb_control_transfer(self.handle, typerequest, request, value, index, data_ptr, length,
                                                  self.TIMEOUT)
            assert dbg == length


class usb3(usb):
    """ classe concue pour la gestion de l'usb3
    """

    def __init__(self, my_vid=0xFE27, my_pid=0xAC01):
        usb.__init__(self, my_vid=my_vid, my_pid=my_pid)
        self.version = 3
        print ("liaison par USB3")

    def write_command(self, request, data_ptr, length):
        """
        fonction qui envoie une commande de controle via USB

        :param request: signature du commande controle
        :param data_ptr: data du commande controle
        :param length: taille de data_ptr
        :return:
        """
        typerequest = self.LIBUSB_RECIPIENT_DEVICE | self.LIBUSB_REQUEST_TYPE_VENDOR | self.LIBUSB_ENDPOINT_OUT
        value = 0
        index = 0
        dbg = libusb1.libusb_control_transfer(self.handle, typerequest, request, value, index, data_ptr, length,
                                              self.TIMEOUT)
        assert dbg == length

    def commande(self, nb_arg, buf):
        """ commande pour le module haut ie les micros"""
        request = 0xB0 + nb_arg
        self.write_command(request, buf, nb_arg + 1)


class MegaMicros():
    """
    Class Megamicros : objet principal de communication avec le module d'acquisition
    """

    def __init__(self, duree=0.00, filename='toto.dat', path='.',
                 mems=np.ones((16, 8), np.bool), va=np.ones((4), np.bool), vl=0, cpt=1,
                 clockdiv=9, interactif=0, verbose=0, addr=0x82):
        """
        Initialisation de la classe Megamicros

        :param duree:       [float]  duree en secondes
        :param filename:    [str]    nom du fichier de donnees
        :param path:        [str]    chemin du fichier de donnees
        :param mems:        [bool np.array(16,8)] tableau indiquant la position des mems actifs
        :param va:          [bool np.array(4,)]   tableau indiquant la position des voies analogiques actives
        :param vl:          [bool np.array(4,)]   tableau indiquant la position des voies logiques actives
        :param cpt:         [int] flag indiquant si le compteur est actif
        :param clockdiv:    [int] valaur de l'horloge (9 correspond a une frequence d echantillonnage de 50kHz

        :return:
        """
        self.filename = filename
        self.path = path
        self.fichier = self.path + '/' + self.filename
        if interactif == 0:
            self.Filep = open(self.fichier, 'wb+')
        self.duree = float(duree)
        self.mems = mems
        self.va = va
        self.vl = vl
        self.cpt = cpt
        self.verbose = verbose

        # initialisation des differentes donnees : techniques, internes et stockage et usb
        self.clockdiv = clockdiv  # 9 corespond a freq = 50kHz   => freq = 500kHz/(clockdiv+1)
        self.init_technical_data(s_pkt=np.sum(self.mems)*1024, n_tdf=8, timeout=1000, addr=addr)
        self.compute_technical_data()
        self.init_util_var()


        # Initialisation des differents modules usb et megamicros

        self.interactif = interactif
        # Gestion de l interactivite
        if self.interactif == 1:
            self.duree_ideale_buffer = int(5 * self.frequence * self.nb_voies)  # par defaut 30 sec
            self.data_len = int(self.duree_ideale_buffer / (self.s_pkt / 4)) * (self.s_pkt / 4)
            self.data = np.zeros((self.data_len,)).astype(np.int32)
            self.data_ptr = 0
            self.data_ptr_lenmax = len(self.data)
            self.data_ptr_R = 0
            self.data_ptr_retour = 0
            self.last_data_ptr = 0

    def init_util_var(self):
        """
        Definition des variable internes utiles au module d'acquisition
        :return:
        """

        self.buf = ctypes.create_string_buffer(16)  # buffer utilise pour envoyer les commandes au systeme
        self.transfert = {}  # dictionnaire d'objets qui contiennent des infos sur les mini buffers
        self.num_pkt = 0  # id du paquet courant
        self.BBUFFER = ctypes.create_string_buffer(int(self.n_tdf * self.s_pkt))  # buffer principal
        self.bbuffer_p = {}  # dictionnaire contenant les adresses memoires des sous buffers (contigus dans BBUFFER)
        for i in range(self.n_tdf):
            self.bbuffer_p[i] = ctypes.addressof(self.BBUFFER) + i * self.s_pkt
        CMPFUNC = ctypes.CFUNCTYPE(None, libusb1.libusb_transfer_p)
        self.fn_callback_c = CMPFUNC(self.fn_callback_py)
        self.last_pkt = 0

    def init_technical_data(self, s_pkt=512*1024, n_tdf=8, timeout=1000, addr=0x82):
        # donnees techniques Mm

        self.frequence = np.double(500000 / (self.clockdiv + 1))  # frequence d ' echantilonnage
        self.datatype = "int32"  # type des donnes transmises par le systeme
        # Attention les 2 voies logiques sont codees sur le meme octet
        self.nb_voies = np.sum(self.mems) + np.sum(self.va) + self.cpt + self.vl
        print 50 * '_'        
        print self.nb_voies
        print 50 * '_'
        self.s_pkt = s_pkt#self.nb_voies * (8 * 1024)  # ATTENTION doit etre multiple de 512octets
        self.n_tdf = n_tdf  # nombre de tache de fond
        self.TIMEOUT = timeout
        self._ADDR = addr
        self.NULL = None
        #print (50 * 'u')
        #print (self.s_pkt)

    def init_transfert_usb(self):
        print ("initialisation du transfert usb <-> Mm")
        for i in range(self.n_tdf):
            self.transfert[i] = libusb1.libusb_alloc_transfer(0)
            libusb1.libusb_fill_bulk_transfer(self.transfert[i], self.usbh.handle, self._ADDR, self.bbuffer_p[i],
                                              self.s_pkt,
                                              self.fn_callback_c, self.NULL, self.TIMEOUT)
            retour = libusb1.libusb_submit_transfer(self.transfert[i])
            if retour:
                print ("Erreur " + str(retour) + " au lancement du paquet" + str(i))
                # else:
                #    print "Pret a recevoir"
        print ("initialisation du transfert usb <-> Mm .................... ok")
        self.etat=1
    def compute_technical_data(self):
        self.COUNT = long(np.floor(self.duree * self.frequence))  # nombre d echantillons a recuperer sur chaque voie
        self.n_pkt = long(np.ceil((4. * self.COUNT * self.nb_voies) / self.s_pkt))  # nombre de paquets a recevoir
        self.s_l_pkt = (
                           4 * self.COUNT * self.nb_voies) % self.s_pkt  # taille du dernier paquet (car s_pkt n est pas comensurable avec count)
        self.check_n_tdf()
        self.tot = 4 * self.nb_voies * self.COUNT  # // nombre de données attendues

    def check_n_tdf(self):
        """
        verifie que le nombre de tache de fond (n_tdf) est compatible avec le nombre de paquets a recuperer

        :return: self._n_tdf = self.n_pkt si self._n_tdf > self.n_pkt
        """
        if self.n_pkt < self.n_tdf:
            self.n_tdf = self.n_pkt

    def SelectChannels(self, nb_faisceaux=16, nb_micros=8):
        """ Active les voies pour lesquels il y a des donnees a recuperer

        ATTENTION : par defaut toutes les voies sont activees !! => a ameliorer


        :param nb_faisceaux:
        :param nb_micros:
        :return:
        """
        if self.mems == 'all':
            self.active_mems = np.ones((nb_faisceaux, nb_micros), np.bool)
        else:
            self.active_mems = self.mems

        if self.va == 'all':
            self.active_va = np.ones((4,), np.bool)
        else:
            self.active_va = self.va

        self.active_cpt = self.cpt

        self.page = {}
        # Setup MEMS pages:
        for i in range(nb_faisceaux):
            ipage = 0
            for chnl in range(nb_micros):
                ipage += self.active_mems[i][chnl] << chnl
            self.page[i] = struct.pack('B', ipage)

        # Setup VA and count page:
        ipage = (self.active_va[0] << 0) + \
                (self.active_va[1] << 1) + \
                (self.active_va[2] << 2) + \
                (self.active_va[3] << 3) + \
                (self.active_cpt << 7)
        self.page[nb_faisceaux] = struct.pack('B', ipage)


    def fn_callback_py(self, transfer_i):
        if self.verbose == 1:
            print ("callback, num_pkt = " + str(self.num_pkt + 1) + " / " + str(self.n_pkt))
        # --------------------------------------------------------------------------------------------------
        # 1 le transfert s est mal passe
        # --------------------------------------------------------------------------------------------------
        if transfer_i.contents.status != libusb1.LIBUSB_TRANSFER_COMPLETED:
            if transfer_i.contents.status == libusb1.LIBUSB_TRANSFER_TIMED_OUT:
                print ("TIMEOUT lors du transfert du paquet" + str(self.num_pkt + 1))
            else:
                print ("Erreur lors du transfert du paquet " + str(transfer_i.contents.status))
            libusb1.libusb_cancel_transfer(transfer_i)
        # --------------------------------------------------------------------------------------------------
        # 2 le transfert s est bien passe
        # --------------------------------------------------------------------------------------------------
        else:
            # ++++++++++++++++++++++++++++++++++++++++++
            # 2.1 Sauvegarde des donnees sur le disque dur
            # ++++++++++++++++++++++++++++++++++++++++++
            if self.interactif == 0:
                self.buffer2disque()
            elif self.interactif == 1:
                self.buffer2buffer()
            # ++++++++++++++++++++++++++++++++++++++++++
            # 2.2 Relance des transferts
            # ++++++++++++++++++++++++++++++++++++++++++
            self.relance_transfert(transfer_i)
            # ++++++++++++++++++++++++++++++++++++++++++
            # 2.2 On incremente le nombre de paquets traites
            # ++++++++++++++++++++++++++++++++++++++++++
            self.num_pkt += 1

    def buffer2disque(self):
        """
        transfert le contenu du buffer courant dans le fichier ouvert sur le disque

        :return:
        """
        if self.num_pkt < self.n_pkt - 1:
            # 2.1.1 Cas standard => le paquet recu est un paquet de longueur normale
            if self.filename:
                adr_debut = (self.num_pkt % self.n_tdf) * self.s_pkt
                adr_fin = adr_debut + self.s_pkt
                self.Filep.write(self.BBUFFER[adr_debut:adr_fin])
            # ATTENTION : si le paquet a une taille standard mais que c'est le dernier paquet a avoir cette taille
            #       il envoie l info via le flag self.last_pkt
            if self.num_pkt == self.n_pkt - 2:
                self.last_pkt = 1
        else:
            # 2.1.2 Cas particulier  => le paquet recu n'est pas un paquet de longueur normale
            #               c'est le dernier paquet de la liste avec une longueur self.s_l_pkt
            if self.filename:
                adr_debut = (self.num_pkt % self.n_tdf) * self.s_pkt
                adr_fin = adr_debut + self.s_l_pkt
                self.Filep.write(self.BBUFFER[adr_debut:adr_fin])

    def buffer2buffer(self):
        """
        transfert le contenu du buffer courant dans le fichier ouvert sur le disque

        :return:
        """
        if self.num_pkt < self.n_pkt - 1:
            # 2.1.1 Cas standard => le paquet recu est un paquet de longueur normale
            adr_debut = (self.num_pkt % self.n_tdf) * self.s_pkt
            adr_fin = adr_debut + self.s_pkt
            size = (adr_fin - adr_debut) / 4
            if self.data_ptr + size > self.data_ptr_lenmax:
                self.last_data_ptr = self.data_ptr
                self.data_ptr = 0
                self.data_ptr_retour = 1
            self.data[self.data_ptr:self.data_ptr + size] = np.frombuffer(self.BBUFFER[adr_debut:adr_fin], np.int32)
            self.data_ptr = self.data_ptr + size
            # self.Filep.write(self.BBUFFER[adr_debut:adr_fin])
            if self.num_pkt == self.n_pkt - 2:
                
                self.last_pkt = 1
        else:
            # 2.1.2 Cas particulier  => le paquet recu n'est pas un paquet de longueur normale
            #               c'est le dernier paquet de la liste avec une longueur self.s_l_pkt
            adr_debut = (self.num_pkt % self.n_tdf) * self.s_pkt
            adr_fin = adr_debut + self.s_l_pkt
            size = (adr_fin - adr_debut) / 4
            if self.data_ptr + size > self.data_ptr_lenmax:
                self.last_data_ptr = self.data_ptr
                self.data_ptr = 0
                self.data_ptr_retour = 1
            self.data[self.data_ptr:self.data_ptr + size] = np.frombuffer(self.BBUFFER[adr_debut:adr_fin], np.int32)
            self.data_ptr = self.data_ptr + size
            # self.Filep.write(self.BBUFFER[adr_debut:adr_fin])

    def get_data(self, duree):
        """
        Va chercher dans Mm les donnees d une duree de 'duree'

        :param duree:
        :return:
        res = 1  si la fct retourne un buffer rempli
        res = 0 si la fct ne retourne rien

        data2 buffer contenant les donnees demandees
        """
        nb_tixels = int(duree * self.frequence)
        # on calcule la longueur du buffer a recuperer
        size = long(nb_tixels * self.nb_voies)
        # on verifie que cette longueur existe
        res = 0
        data2 = np.zeros(nb_tixels , self.nb_voies).astype(np.int32)
        tmp = np.zeros(nb_tixels  * self.nb_voies).astype(np.int32)

        if self.data_ptr_R + size < len(self.data):
            # print "donnees contigues"
            if self.data_ptr > self.data_ptr_R + size:  # or self.data_ptr_retour == 1:
                res = 1
                # print "bloc pret pour lecture"
                if self.data_ptr_R + size < len(self.data):
                    data2 = self.data[self.data_ptr_R:self.data_ptr_R + size].reshape(
                        (nb_tixels, self.nb_voies))
                    self.data_ptr_R = self.data_ptr_R + size

            else:
                # print "bloc non pret pour lecture"
                res = 0

        else:
            # print "pb:::::::::"
            size_end = self.last_data_ptr - self.data_ptr_R
            if (size_end + self.data_ptr > size) and (self.data_ptr_retour == 1):
                # on calcule la duree corresondant a size_end
                # duree_partielle = size_end / self.frequence / self.nb_voies
                # print size_begin
                # print size_end
                # print size
                # print size_end/self.nb_voies
                # print self.nb_voies

                # print np.shape(data2[0:size_end,:])
                tmp1 = self.data[self.data_ptr_R:self.last_data_ptr]
                tmp2 = self.data[0:size - size_end]
                # print size_end
                # print self.data_ptr
                tmp[0:len(tmp1)] = tmp1
                tmp[len(tmp1):] = tmp2
                data2 = tmp.reshape((nb_tixels, self.nb_voies))
                self.data_ptr_R = size - size_end
                self.data_ptr_retour = 0
                # data2[size_end:size - size_end,:]
                res = 1
            else:
                res = 0
                # print "donnees non contigues"

        return res, data2

    def relance_transfert(self, transfer_i):
        """
        relance (ou pas) le transfert du buffer courant

        :param transfer_i:
        :return:
        """

        # calcul du numero du pkt si on le relance
        id_futur = self.num_pkt + self.n_tdf
        if id_futur == self.n_pkt - 1:
            # le paquet sera le dernier de la liste :
            # avant de le relancer, il faut changer la taille du buffer attendu
            # on allonge egalement la taille du timeout pour avoir le temps de lancer l instruction packend
            libusb1.libusb_fill_bulk_transfer(transfer_i, self.usbh.handle, self._ADDR,
                                              self.bbuffer_p[self.num_pkt % self.n_tdf],
                                              self.s_l_pkt, self.fn_callback_c, NULL, 10 * self.TIMEOUT)
            # on relance le transfert
            retour = libusb1.libusb_submit_transfer(transfer_i)
            if retour:
                print (".....Erreur " + str(retour) + " au lancement transfert du dernier paquet " + str(self.num_pkt))
                # else:
                #    print "dernier paquet, s_pkt = " + str(self.s_l_pkt)
        elif id_futur < self.n_pkt - 1:
            # le paquet sera un paquet (normal) dans la liste :
            # on relance le transfert
            retour = libusb1.libusb_submit_transfer(transfer_i)
            if retour:
                print (".....Erreur " + str(retour) + " au lancement du paquet " + str(self.num_pkt))
                # else:
                #    print "paquet standard"
        elif id_futur > self.n_pkt - 1 or self.etat==0:
            # le paquet ne sera pas un paquet de la liste :
            # on ne relance pas le transfert
            pass

    def stop(self):
        self.last_pkt = 1
        self.etat=0

    def show(self):
        """
        boucle interne de megamicros pour permettre l'acquisition et la gestion des evenements
        :return:
        """
        LIBUSB_SUCCESS = libusb1.LIBUSB_SUCCESS
        rc = 0
        while rc == LIBUSB_SUCCESS and self.num_pkt < self.n_pkt:

            rc = libusb1.libusb_handle_events(NULL)
            #print("ac")
            if self.last_pkt == 1 and self.usbh.version == 2:
                msg = ctypes.create_string_buffer(16)
                print(self.num_pkt)
                print ('packet end')
                if(self.interactif==1):
                    self.num_pkt = self.n_pkt
                time.sleep(1)
                self.usbh.write_command(0xC1, msg, 0)

            if rc != LIBUSB_SUCCESS:
                print ("ERREUR dans la gestion des events")
                break

    def __str__(self):
        chaine = 50 * '=' + '\n'
        chaine = chaine + '' + '\n'
        chaine = chaine + ' Megamicros ' + str(self.version) + '\n'
        chaine = chaine + ' ' + '\n'
        chaine = chaine + "duree d'acquisition : " + str(self.duree) + '\n'
        chaine = chaine + "nombre de voies d'acquisition : " + str(self.nb_voies) + '\n'
        chaine = chaine + "nombre d'octets a acquerir : " + str(self.tot) + '\n'
        chaine = chaine + "nombre de paquets :" + str(self.n_pkt) + '\n'
        chaine = chaine + "nombre de taches de fond : " + str(self.n_tdf) + '\n'
        chaine = chaine + "taille des paquets : " + str(self.s_pkt) + '\n'
        chaine = chaine + "taille du dernier paquet : " + str(self.s_l_pkt) + '\n'
        chaine = chaine + 50 * '=' + '\n'
        return chaine
