import os

class Param(object):
    """
    ptychography reconstruction parameters
    """
    def __init__(self):
        # from recon_ptycho.py
        # organized by grouping in GUI

        #
        # [Data]
        #
        self.scan_num = '34784'       # scan number
        self.detectorkind = 'merlin1' # ['merlin1', 'merlin2', 'timepix1', 'timepix2']
        self.frame_num = 0            # frame number to check

        #
        # [Experimental parameters]
        #
        self.xray_energy = 0.
        self.detector_distance = 0.
        self.x_arr_size = 0.
        self.x_step_size = 0.
        self.x_scan_range = 0.
        self.y_arr_size = 0.
        self.y_step_size = 0.
        self.y_scan_range = 0.


        #
        # [RUN]
        #
        self.sign = 't1'             # saving file name
        self.n_iterations = 50       # number of iterations
        self.p_flag = False          # True to load an exsiting probe
        self.distance = 0.           # ???
        self.mode_flag = False       # do multi-mode reconstruction
        self.gpu_flag = True         # whether to use GPU
        self.gpus = None             # should be a list of gpu numbers, ex: [0, 2, 3]
        self.prb_path = None         # path to existing probe array (.npy)
        self.obj_path = None         # path to existing object array (.npy)

        #
        # [EXPERT]
        #
        self.mesh_flag = 1
        self.start_ave = 0.8

        self.nth = 5                 # number of points in the first ring
        self.ccd_pixel_um = 55.      # detector pixel size (um)

        # scan direction and geomety correction handling
        self.cal_scan_pattern_flag = False

        self.alg_flag = 'DM'         # choose from 'DM', 'ML', 'ER'
        self.ml_mode = 'Poisson'     # mode for ML
        self.alg2_flag = 'DM'        # choose from 'DM', 'ML', 'ER'
        self.alg_percentage = .8

        # param for Bragg mode
        self.bragg_flag = False
        self.bragg_theta = 69.41
        self.bragg_gamma = 33.4
        self.bragg_delta = 15.458

        self.amp_max = 1.    # up/low limit of allowed object amplitude range
        self.amp_min = 0.5   #
        self.pha_max = 0.01  # up/low limit of allowed object phase range
        self.pha_min = -1.0  #

        # partial coherence parameter
        self.pc_flag = False
        self.pc_sigma = 2.    # initial guess of kernel sigma
        self.pc_alg = 'lucy'  # deconvolution algorithm, lucy or wiener
        self.pc_kernel_n = 32

        # reconstruction feedback parameters
        self.alpha = 1.e-8
        self.beta = 0.9

        # mode calculation parameter
        self.save_tmp_pic_flag = False
        self.prb_mode_num = 5
        self.obj_mode_num = 1

        # position correction parameter
        self.position_correction_flag = False
        self.position_correction_start = 50
        self.position_correction_step = 10

        # multislice parameter
        self.multislice_flag = False
        self.slice_num = 2
        self.slice_spacing_m = 5.e-6

        self.start_update_probe = 0 # iteration number to start updating probe
        self.start_update_object = 0

        self.init_obj_flag = True # True: random guess; False: load an array
        self.init_obj_dpc_flag = False
        self.prb_center_flag = True
        self.init_prb_flag = False # True: random guess; False: load an array
        self.mask_prb_flag = False

        self.dm_version = 1
        self.sf_flag = False
        self.ms_pie_flag = False
        self.weak_obj_flag = False
        self.processes = 0



        #
        # [DEFAULT]
        #

    def get_alg_flg_index(self):
        return ['DM', 'ML', 'ER'].index(self.alg_flag)

    def get_ml_model_index(self):
        return ['Poisson'].index(self.ml_mode)

    def get_alg2_flg_index(self):
        return ['DM', 'ML', 'ER'].index(self.alg2_flag)

    def get_pc_alg_index(self):
        return ['lucy', 'wiener'].index(self.pc_alg)


















