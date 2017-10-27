def lecture_dat(nomfic, n_channels):
    """
    """
    f = open(nomfic)
    A = np.fromfile(f, dtype = np.int32)
    sz = np.size(A)/n_channels
    Data = A.reshape((sz, n_channels))
    return Data