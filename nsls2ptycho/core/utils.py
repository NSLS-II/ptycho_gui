import getpass
import os
from pwd import getpwuid
import sys

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

from nsls2ptycho.core.ptycho.utils import split


# DEPRECARED: migrated to nsls2ptycho.core.widgets.mplcanvas
def plot_point_process_distribution(pts, mpi_size, colormap=cm.jet):
    '''
    Plot N scanning points in mpi_size different colors

    Parameters:
        - pts: np.array([[x0, x1, ..., xN], [y0, y1, ..., yN]])
        - mpi_size: number of MPI processes
        - colormap 
    '''
    a = split(pts.shape[1], mpi_size)
    colors = colormap(np.linspace(0, 1, len(a)))
    for i in range(mpi_size):
        plt.scatter(pts[0, a[i][0]:a[i][1]], pts[1, a[i][0]:a[i][1]], c=colors[i])
    plt.show()

def find_owner(filename):
    # from https://stackoverflow.com/a/1830635
    return getpwuid(os.stat(filename).st_uid).pw_name

def clean_shared_memory(pid=None):
    '''
    This function cleans up shared memory segments created by the GUI or a buggy Open MPI.
    '''
    # this only works for linux that has /dev/shm
    if not sys.platform.startswith('linux'):
        print("This function works only under Linux. Stop.", file=sys.stderr)
        return
    assert os.path.isdir('/dev/shm/')

    from posix_ipc import SharedMemory
    shm_list = os.listdir('/dev/shm/')
    user = getpass.getuser()   

    for shm in shm_list:
        if (shm.startswith('ptycho') or shm.startswith('vader')) \
           and user == find_owner('/dev/shm/'+shm):

            if (pid is None) or (pid is not None and pid in shm):
                s = SharedMemory("/"+shm)
                s.close_fd()
                s.unlink()

    print("Done.")
