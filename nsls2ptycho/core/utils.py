import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from nsls2ptycho.core.ptycho.utils import split


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
