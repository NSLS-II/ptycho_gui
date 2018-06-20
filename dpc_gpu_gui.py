import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog

from ui import ui_dpc
from core.dpc_param import Param
from core.dpc_recon import DPCReconWorker, DPCReconFakeWorker
from core.dpc_qt_utils import DPCStream
from core.widgets.mplcanvas import load_image_pil

# databroker related
# TODO: a try-except for ImportError??
try:
    from core.HXN_databroker import db1, db2, db_old, load_metadata
    from hxntools.scan_info import ScanInfo
except ImportError as ex:
    print('[!] Unable to import hxntools-related packages some features will '
          'be unavailable')
    print('[!] (import error: {})'.format(ex))

from reconStep_gui import ReconStepWindow
from roi_gui import RoiWindow

import h5py
import numpy as np
from numpy.lib.format import open_memmap
import matplotlib.pyplot as plt
import traceback


# set True for testing GUI changes
_TEST = False


class MainWindow(QtWidgets.QMainWindow, ui_dpc.Ui_MainWindow):
    def __init__(self, parent=None, param:Param=None):
        super().__init__(parent)
        self.setupUi(self)
        QtWidgets.QApplication.setStyle('Plastique')

        # connect
        self.btn_load_probe.clicked.connect(self.loadProbe)
        self.btn_load_object.clicked.connect(self.loadObject)
        self.ck_init_prb_flag.clicked.connect(self.updateProbeFlg)
        self.ck_init_obj_flag.clicked.connect(self.updateObjectFlg)

        self.btn_choose_cwd.clicked.connect(self.setWorkingDirectory)
        self.cb_dataloader.currentTextChanged.connect(self.setLoadButton)
        self.btn_load_scan.clicked.connect(self.loadExpParam)
        self.btn_view_frame.clicked.connect(self.viewDataFrame)

        self.le_scan_num.editingFinished.connect(self.forceLoad)
        self.cb_dataloader.currentTextChanged.connect(self.forceLoad)
        self.cb_detectorkind.currentTextChanged.connect(self.forceLoad)

        self.ck_mode_flag.clicked.connect(self.updateModeFlg)
        self.ck_multislice_flag.clicked.connect(self.updateMultiSliceFlg)
        self.ck_gpu_flag.clicked.connect(self.updateGpuFlg)

        self.btn_recon_start.clicked.connect(self.start)
        self.btn_recon_stop.clicked.connect(self.stop)
        self.btn_recon_batch_start.clicked.connect(self.batch_start)
        self.btn_recon_batch_stop.clicked.connect(self.batch_stop)

        self.btn_MPI_file.clicked.connect(self.setMPIfile)
        self.btn_gpu_all = [self.btn_gpu_0, self.btn_gpu_1, self.btn_gpu_2, self.btn_gpu_3]
        for btn in self.btn_gpu_all:
            btn.clicked.connect(self.updateMPIFlg)

        # init.
        if param is None:
            self.param = Param() # default
        else:
            self.param = param
        self._prb = None
        self._obj = None
        self._dpc_gpu_thread = None
        self._db = None             # hold the Broker instance that contains the info of the given scan id
        self._mds_table = None      # hold a Pandas.dataframe instance
        self._loaded = False        # whether the user has loaded metadata or not (from either databroker or h5)
        self._scan_numbers = None   # a list of scan numbers for batch mode

        self.reconStepWindow = None

        self.update_gui_from_param()
        self.updateModeFlg()
        self.updateMultiSliceFlg()
        self.updateGpuFlg()
        self.resetButtons()
        self.resetExperimentalParameters() # probably not necessary
        self.setLoadButton()


    @property
    def db(self):
        # access the Broker instance; the name is probably not intuitive enough...?
        return self._db


    @db.setter
    def db(self, scan_id:int):
        # choose the correct Broker instance based on the given scan id
        if scan_id <= 34000:
            self._db = db_old
        elif scan_id <= 48990:
            self._db = db1
        else:
            self._db = db2


    def resetButtons(self):
        self.btn_recon_start.setEnabled(True)
        self.btn_recon_stop.setEnabled(False)
        self.btn_recon_batch_start.setEnabled(True)
        self.btn_recon_batch_stop.setEnabled(False)
        self.recon_bar.setValue(0)
        #plt.ioff()
        plt.close('all')
        # close the mmap arrays
        # removing these arrays, can be changed later if needed
        if self._prb is not None:
            del self._prb
            self._prb = None
            os.remove(self.param.working_directory + '.mmap_prb.npy')
        if self._obj is not None:
            del self._obj
            self._obj = None
            os.remove(self.param.working_directory + '.mmap_obj.npy')
        

    def update_param_from_gui(self):
        p = self.param
        p.scan_num = str(self.le_scan_num.text())
        p.sign = str(self.le_sign.text())
        p.detectorkind = str(self.cb_detectorkind.currentText())
        # p.frame_num = int(self.sp_fram_num.value()) # do we need this one?

        # p.xray_energy = float(self.sp_xray_energy.value()) # do we need this one?
        p.lambda_nm = 1.2398/self.sp_xray_energy.value()
        p.z_m = float(self.sp_detector_distance.value())
        #p.x_arr_size = float(self.sp_x_arr_size.value()) # can get from diffamp
        p.dr_x = float(self.sp_x_step_size.value())
        p.x_range = float(self.sp_x_scan_range.value())
        #p.y_arr_size = float(self.sp_y_arr_size.value()) # can get from diffamp
        p.dr_y = float(self.sp_y_step_size.value())
        p.y_range = float(self.sp_y_scan_range.value())
        #p.scan_type = str(self.cb_scan_type.currentText()) # do we need this one?
        #p.num_points = int(self.sp_num_points.value()) # can get from diffamp

        p.n_iterations = int(self.sp_n_iterations.value())
        p.alg_flag = str(self.cb_alg_flag.currentText())
        p.alg2_flag = str(self.cb_alg2_flag.currentText())
        p.alg_percentage = float(self.sp_alg_percentage.value())

        p.init_prb_flag = self.ck_init_prb_flag.isChecked()
        p.init_obj_flag = self.ck_init_obj_flag.isChecked()

        p.mode_flag = self.ck_mode_flag.isChecked()
        p.prb_mode_num = self.sp_prb_mode_num.value()
        p.obj_mode_num = self.sp_obj_mode_num.value()
        if p.mode_flag:
            p.sign = p.sign + "_mode"

        p.multislice_flag = self.ck_multislice_flag.isChecked()
        p.slice_num = int(self.sp_slice_num.value())
        p.slice_spacing_m = float(self.sp_slice_spacing_m.value() * 1e-6)
        if p.multislice_flag:
            p.sign = p.sign + "_ms"
        p.distance = float(self.sp_distance.value())

        p.amp_min = float(self.sp_amp_min.value())
        p.amp_max = float(self.sp_amp_max.value())
        p.pha_min = float(self.sp_pha_min.value())
        p.pha_max = float(self.sp_pha_max.value())

        p.gpu_flag = self.ck_gpu_flag.isChecked()
        gpus = []
        for btn_gpu, id in zip(self.btn_gpu_all, range(len(self.btn_gpu_all))):
            if btn_gpu.isChecked():
                gpus.append(id)
        p.gpus = gpus

        p.angle_correction_flag = self.ck_angle_correction_flag.isChecked()
        p.x_direction = float(self.sp_x_direction.value())
        p.y_direction = float(self.sp_y_direction.value())
        p.angle = self.sp_angle.value()

        p.alpha = float(self.sp_alpha.value()*1.e-8)
        p.beta = float(self.sp_beta.value())

        p.display_interval = int(self.sp_display_interval.value())


    def update_gui_from_param(self):
        p = self.param
        self.le_scan_num.setText(p.scan_num)
        self.le_sign.setText(p.sign)
        self.cb_detectorkind.setCurrentIndex(p.get_detector_kind_index())
        self.sp_fram_num.setValue(int(p.frame_num))

        self.sp_xray_energy.setValue(1.2398/float(p.lambda_nm) if 'lambda_nm' in p.__dict__ else 0.)
        self.sp_detector_distance.setValue(float(p.z_m) if 'z_m' in p.__dict__ else 0)
        self.sp_x_arr_size.setValue(float(p.x_arr_size))
        self.sp_x_step_size.setValue(float(p.x_step_size))
        self.sp_x_scan_range.setValue(float(p.x_scan_range))
        self.sp_y_arr_size.setValue(float(p.y_arr_size))
        self.sp_y_step_size.setValue(float(p.y_step_size))
        self.sp_y_scan_range.setValue(float(p.y_scan_range))
        self.cb_scan_type.setCurrentIndex(p.get_scan_type_index())
        self.sp_num_points.setValue(int(p.num_points))

        self.sp_n_iterations.setValue(int(p.n_iterations))
        self.cb_alg_flag.setCurrentIndex(p.get_alg_flg_index())
        self.cb_alg2_flag.setCurrentIndex(p.get_alg2_flg_index())
        self.sp_alg_percentage.setValue(float(p.alg_percentage))

        self.ck_init_prb_flag.setChecked(p.init_prb_flag)
        self.le_prb_path.setText(str(p.prb_filename or ''))

        self.ck_init_obj_flag.setChecked(p.init_obj_flag)
        self.le_obj_path.setText(str(p.obj_filename or ''))

        self.le_working_directory.setText(str(p.working_directory or ''))

        self.ck_mode_flag.setChecked(p.mode_flag)
        self.sp_prb_mode_num.setValue(int(p.prb_mode_num))
        self.sp_obj_mode_num.setValue(int(p.obj_mode_num))

        self.ck_multislice_flag.setChecked(p.multislice_flag)
        self.sp_slice_num.setValue(int(p.slice_num))
        self.sp_slice_spacing_m.setValue(p.get_slice_spacing_m())
        self.sp_distance.setValue(float(p.distance))

        self.sp_amp_max.setValue(float(p.amp_max))
        self.sp_amp_min.setValue(float(p.amp_min))
        self.sp_pha_max.setValue(float(p.pha_max))
        self.sp_pha_min.setValue(float(p.pha_min))

        self.ck_gpu_flag.setChecked(p.gpu_flag)
        for btn_gpu, id in zip(self.btn_gpu_all, range(len(self.btn_gpu_all))):
            btn_gpu.setChecked(id in p.gpus)

        self.ck_angle_correction_flag.setChecked(p.angle_correction_flag)
        self.sp_x_direction.setValue(p.x_direction)
        self.sp_y_direction.setValue(p.y_direction)
        self.sp_angle.setValue(p.angle)

        self.sp_alpha.setValue(p.alpha * 1e+8)
        self.sp_beta.setValue(p.beta)

        self.sp_display_interval.setValue(p.display_interval)


    def start(self):
        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isFinished():
            self._dpc_gpu_thread = None

        if self._dpc_gpu_thread is None:
            if not self._loaded:
                print("[WARNING] Remember to click \"Load\" before proceeding!", file=sys.stderr) 
                return

            self.update_param_from_gui() # this has to be done first, so all operations depending on param are correct
            self.recon_bar.setValue(0)
            self.recon_bar.setMaximum(self.param.n_iterations)

            # init reconStepWindow
            if self.ck_preview_flag.isChecked():
                if self.reconStepWindow is None:
                    self.reconStepWindow = ReconStepWindow()
                self.reconStepWindow.reset_window(iterations=self.param.n_iterations,
                                                  slider_interval=self.param.display_interval)
                self.reconStepWindow.show()

            if not _TEST:
                thread = self._dpc_gpu_thread = DPCReconWorker(self.param)
            else:
                thread = self._dpc_gpu_thread = DPCReconFakeWorker(self.param)

            thread.update_signal.connect(self.update_recon_step)
            thread.finished.connect(self.resetButtons)
            #thread.finished.connect(self.reconStepWindow.debug)
            thread.start()

            self.btn_recon_stop.setEnabled(True)
            self.btn_recon_start.setEnabled(False)


    def stop(self):
        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isRunning():
            self._dpc_gpu_thread.kill() # first kill the mpi processes
            self._dpc_gpu_thread.quit() # then quit QThread gracefully
            self._dpc_gpu_thread = None
            self.resetButtons()
            if self.reconStepWindow is not None:
                self.reconStepWindow.reset_window()


    def update_recon_step(self, it, data=None):
        self.recon_bar.setValue(it)

        if self.reconStepWindow is not None:
            self.reconStepWindow.update_iter(it)

            if not _TEST:
                try:
                    if it == 1:
                        # the two npy are created by ptycho by this time
                        self._prb = open_memmap(self.param.working_directory + '.mmap_prb.npy', mode = 'r')
                        self._obj = open_memmap(self.param.working_directory + '.mmap_obj.npy', mode = 'r')
                    if it % self.param.display_interval == 1 or (it >= 1 and self.param.display_interval == 1):
                        # there could be synchronization problem? should have better solution...
                        images = [np.flipud(np.angle(self._obj[it-1, 0]).T),
                                  np.flipud(np.abs(self._obj[it-1, 0]).T),
                                  np.flipud(np.abs(self._prb[it-1, 0]).T),
                                  np.flipud(np.angle(self._prb[it-1, 0]).T)]
                        self.reconStepWindow.update_images(it, images)
                        self.reconStepWindow.update_metric(it, data)
                except TypeError as ex: # when MPI processes are terminated, _prb and _obj are deleted and so not subscriptable 
                    pass
            else:
                # -------------------- Sungsoo version -------------------------------------
                # a list of random images for test
                # in the order of [object_amplitude, object_phase, probe_amplitude, probe_phase]
                images = [np.random.random((128,128)) for _ in range(4)]
                self.reconStepWindow.update_images(it, images)
                self.reconStepWindow.update_metric(it, data)


    def loadProbe(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open probe file', filter="(*.npy)")
        if filename is not None and len(filename) > 0:
            prb_filename = os.path.basename(filename)
            prb_dir = filename[:(len(filename)-len(prb_filename))]
            self.param.set_prb_path(prb_dir, prb_filename)
            self.le_prb_path.setText(prb_filename)
            self.ck_init_prb_flag.setChecked(False)


    def updateProbeFlg(self):
        # called when "estimate from data" is clicked
        self.param.set_prb_path('', '')
        self.le_prb_path.setText('')
        self.ck_init_prb_flag.setChecked(True)


    def loadObject(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open object file', filter="(*.npy)")
        if filename is not None and len(filename) > 0:
            obj_filename = os.path.basename(filename)
            obj_dir = filename[:(len(filename)-len(obj_filename))]
            self.param.set_obj_path(obj_dir, obj_filename)
            self.le_obj_path.setText(obj_filename)
            self.ck_init_obj_flag.setChecked(False)


    def updateObjectFlg(self):
        # called when "random start" is clicked
        self.param.set_obj_path('', '')
        self.le_obj_path.setText('')
        self.ck_init_obj_flag.setChecked(True)


    def setWorkingDirectory(self):
        dirname = QFileDialog.getExistingDirectory(self, 'Choose working folder', directory=os.path.expanduser("~"))
        if dirname is not None and len(dirname) > 0:
            dirname = dirname + "/"
            self.param.set_working_directory(dirname)
            self.le_working_directory.setText(dirname)


    def updateModeFlg(self):
        mode_flag = self.ck_mode_flag.isChecked()
        self.sp_prb_mode_num.setEnabled(mode_flag)
        self.sp_obj_mode_num.setEnabled(mode_flag)
        self.param.mode_flag = mode_flag


    def updateMultiSliceFlg(self):
        flag = self.ck_multislice_flag.isChecked()
        self.sp_slice_num.setEnabled(flag)
        self.sp_slice_spacing_m.setEnabled(flag)
        self.param.multislice_flag = flag


    def updateGpuFlg(self):
        flag = self.ck_gpu_flag.isChecked()
        self.btn_gpu_0.setEnabled(flag)
        self.btn_gpu_1.setEnabled(flag)
        self.btn_gpu_2.setEnabled(flag)
        self.btn_gpu_3.setEnabled(flag)


    def setMPIfile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open MPI machine file')
        if filename is not None and len(filename) > 0:
            mpi_filename = os.path.basename(filename)
            mpi_dir = filename[:(len(filename)-len(mpi_filename))]
            #self.param.le_MPI_file_path(mpi_dir, mpi_filename)
            self.param.mpi_file_path = filename
            #print(filename)
            self.le_MPI_file_path.setText(mpi_filename)
            for btn in self.btn_gpu_all:
                btn.setChecked(False)


    def updateMPIFlg(self):
        # called when any gpu button is clicked
        self.param.mpi_file_path = ''
        self.le_MPI_file_path.setText('')


    # adapted from dpc_batch.py
    def parse_scan_range(self):
        '''
        Note the range is inclusive on both ends. 
        Ex: 1238 - 1242 with step size 2 --> [1238, 1240, 1242]
        '''
        scan_range = []
        scan_numbers = []
        every_nth_scan = self.sp_batch_step.value()

        # first parse items and separate them into two catogories
        slist = self.le_batch_items.text().split(',')
        for item in slist:
            if '-' in item:
                sublist = item.split('-')
                scan_range.append((int(sublist[0].strip()), int(sublist[1].strip())))
            else:
                scan_numbers.append(int(item.strip()))
    
        # next generate all legit items from the chosen ranges and make a sorted item list
        for item in scan_range:
            scan_numbers = scan_numbers + list(range(item[0], item[1]+1, every_nth_scan))
        scan_numbers.sort(reverse=True)
        print(scan_numbers)

        return scan_numbers


    def batch_start(self):
        '''
        Currently only support load from h5. 
        '''
        if self.cb_dataloader.currentText() == "Load from databroker":
            print("[WARNING] Batch mode with databroker is not yet supported. Abort.", file=sys.stderr)
            return

        self._scan_numbers = self.parse_scan_range()
        # TODO: is there a way to lock all widgets to prevent accidental parameter changes in the middle?

        # fire up
        self._batch_manager() # serve as linked list's head
        self.btn_recon_batch_start.setEnabled(False)
        self.btn_recon_batch_stop.setEnabled(True)


    def batch_stop(self):
        '''
        Brute-force abortion of the entire batch. No resumption is possible.
        '''
        self._dpc_gpu_thread.finished.disconnect(self._batch_manager)
        self._scan_numbers = None
        self.stop()


    def _batch_manager(self):
        '''
        This is a "linked list" that utilizes Qt's signal mechanism to retrieve the next item in the list
        when the current item is processed. We need this because most likely the users want to put all
        available computing resources to process the batch item by item, and having more than one worker
        is not helping.
        '''
        # TODO: think what if anything goes wrong in the middle. Is this robust?
        if len(self._scan_numbers) > 0:
            scan_num = self._scan_numbers.pop()
            print("begin processing scan " + str(scan_num) + "...") 
            self.le_scan_num.setText(str(scan_num))
            self.start()
            self._dpc_gpu_thread.finished.connect(self._batch_manager)
        else:
            print("batch processing complete!")
            self._scan_numbers = None
            self.resetButtons()


    def viewDataFrame(self):
        '''
        Correspond to "View & set" in DPC GUI
        '''
        if _TEST:
            image = load_image_pil('./test.tif')
            self.roiWindow = RoiWindow(image=image)
            self.roiWindow.roi_changed.connect(self._get_roi_slot)
            self.roiWindow.show()
            return

        if not self._loaded:
            print("[WARNING] Remember to click \"Load\" before proceeding!", file=sys.stderr) 
            return

        frame_num = self.sp_fram_num.value()
        img = None

        try:
            if self.cb_dataloader.currentText() == "Load from databroker":
                img = self._viewDataFrameBroker(frame_num)
            
            if self.cb_dataloader.currentText() == "Load from h5":
                img = self._viewDataFrameH5(frame_num)
        except OSError:
            # h5 not found, but loadExpParam() has detected it, so do nothing here
            pass
        except (ValueError, RuntimeError) as ex:
            # let user follow the instruction to make correction
            print(ex, file=sys.stderr)
        except Exception as ex:
            # don't expect this will happen but if so I'd like to know what
            self.exception_handler(ex)
        else:
            #img = np.rot90(img, axes=(1,0))
            self.roiWindow = RoiWindow(image=img, main_window=self)
            #self.roiWindow.roi_changed.connect(self._get_roi_slot)
            self.roiWindow.show()


    #@profile
    def _viewDataFrameBroker(self, frame_num:int):
        # assuming at this point the user has clicked "load" 
        if self._mds_table is None:
            raise RuntimeError("[ERROR] Need to click the \"load\" button before viewing.")
        length = (self._mds_table.shape)[0] 
        if frame_num >= length:
            message = "[ERROR] The {0}-th frame doesn't exist. "
            message += "Available frames for the chosen scan: [0, {1}]."
            raise ValueError(message.format(frame_num, length-1))

        img = self.db.reg.retrieve(self._mds_table.iat[frame_num])[0]
        return img


    #@profile
    def _viewDataFrameH5(self, frame_num:int):
        # load the data from the h5 in the working directory
        working_dir = str(self.le_working_directory.text()) # self.param.working_directory
        scan_num = str(self.le_scan_num.text())
        length = self.sp_num_points.value()
        if frame_num >= length:
            message = "[ERROR] The {0}-th frame doesn't exist. "
            message += "Available frames for the chosen scan: [0, {1}]."
            raise ValueError(message.format(frame_num, length-1))
        with h5py.File(working_dir+'/scan_'+scan_num+'.h5','r') as f:
            print("h5 loaded, parsing the {}-th frame...".format(frame_num), end='')
            img = f['diffamp'][frame_num]
            #data = f['diffamp'].value
            #img = data[frame_num]
            print("done")
        return img


    def _get_roi_slot(self, x0, y0, width, height):
        '''
        feel free to rename this function as you need
        : this function to get roi when user click SEND button or
        : dynamically...

        x0: upper left x coordinate
        y0: upper left y coordinate
        width: width
        height: height
        '''
        print(x0, y0, width, height)


    def loadExpParam(self): 
        scan_num = int(self.le_scan_num.text())

        try:
            if self.cb_dataloader.currentText() == "Load from databroker":
                self._loadExpParamBroker(scan_num)

            if self.cb_dataloader.currentText() == "Load from h5":
                self._loadExpParamH5(scan_num)
        except KeyError as ex: # for h5
            if ex.args[0] == 'angle':
                self.sp_angle.setValue(15.) # backward compatibility for old datasets
                print("angle not found, assuming 15...", file=sys.stderr)
            else: # shouldn't happen, and we'd like to know (ex: old scan data from databroker)
                self.exception_handler(ex)
        except OSError: # for h5
            print("[ERROR] h5 not found. Resetting...", file=sys.stderr, end='')
            self.resetExperimentalParameters()
        except ValueError as ex: # for databroker
            print()
            print(ex, file=sys.stderr)
            print("[ERROR] no image available for the chosen detector.", file=sys.stderr)
        except Exception as ex: # everything unexpected at this time...
            self.exception_handler(ex)
        else:
            self._loaded = True
        finally:
            print("done")


    #@profile
    def _loadExpParamBroker(self, scan_id:int):
        #doesn't really work...
        #print("loading begins...may take a while...")
        #sys.stdout.flush()
        self.db = scan_id # set the correct database
        header = self.db[scan_id]

        # get the list of detector names; TODO: a better way without ScanInfo?
        scan = ScanInfo(header)
        det_name = self.cb_detectorkind.currentText()
        det_name_exists = False
        self.cb_detectorkind.clear()
        for detector_name in scan.filestore_keys:
            self.cb_detectorkind.addItem(detector_name)
            if det_name == detector_name:
                det_name_exists = True
        if not det_name_exists:
            det_name = self.cb_detectorkind.currentText()

        # get metadata
        metadata = load_metadata(self.db, scan_id, det_name)
        self.param.__dict__ = {**self.param.__dict__, **metadata} # for Python 3.5+ only
        if metadata['nz'] == 0:
            raise ValueError
        else:
            nz = metadata['nz']
            # get the mds keys to the image (diffamp) array 
            self._mds_table = metadata['mds_table']

        print("databroker connected, parsing experimental parameters...", end='')
        # get nx and ny by looking at the first image
        img = self.db.reg.retrieve(self._mds_table.iat[0])[0]
        nx, ny = img.shape # can also give a ValueError; TODO: come up a better way!
        self.sp_xray_energy.setValue(metadata['energy_kev'])
        #self.sp_detector_distance.setValue(f['z_m'].value) # don't know how to handle this...
        self.sp_x_arr_size.setValue(nx)
        self.sp_y_arr_size.setValue(ny)
        self.sp_num_points.setValue(nz)
        self.sp_x_step_size.setValue(metadata['dr_x'])
        self.sp_y_step_size.setValue(metadata['dr_y'])
        self.sp_x_scan_range.setValue(metadata['x_range'])
        self.sp_y_scan_range.setValue(metadata['y_range'])
        self.sp_angle.setValue(metadata['angle'])
        if self.cb_scan_type.findText(metadata['scan_type']) == -1:
            self.cb_scan_type.addItem(metadata['scan_type'])
        self.cb_scan_type.setCurrentText(metadata['scan_type'])


    def setLoadButton(self):
        if self.cb_dataloader.currentText() == "Load from databroker":
            self.cb_detectorkind.setEnabled(True)
            self.cb_scan_type.setEnabled(True)
            print("[WARNING] Currently detector distance is unavailable in Databroker and must be set manually!", file=sys.stderr)
        if self.cb_dataloader.currentText() == "Load from h5":
            self.cb_detectorkind.setEnabled(False)
            self.cb_scan_type.setEnabled(False) # do we ever write scan type to h5???


    #@profile
    def _loadExpParamH5(self, scan_num:int):
        # load the parameters from the h5 in the working directory
        working_dir = str(self.le_working_directory.text()) # self.param.working_directory
        with h5py.File(working_dir+'/scan_'+str(scan_num)+'.h5','r') as f:
            # this code is not robust enough as certain keys may not be present...
            print("h5 loaded, parsing experimental parameters...", end='')
            self.sp_xray_energy.setValue(1.2398/f['lambda_nm'].value)
            self.sp_detector_distance.setValue(f['z_m'].value)
            nz, nx, ny = f['diffamp'].shape
            self.sp_x_arr_size.setValue(nx)
            self.sp_y_arr_size.setValue(ny)
            self.sp_x_step_size.setValue(f['dr_x'].value)
            self.sp_y_step_size.setValue(f['dr_y'].value)
            self.sp_x_scan_range.setValue(f['x_range'].value)
            self.sp_y_scan_range.setValue(f['y_range'].value)
            self.sp_angle.setValue(f['angle'].value)
            #self.cb_scan_type = ...
            self.sp_num_points.setValue(nz)
            # read the detector name and set it in GUI??


    def resetExperimentalParameters(self):
        self.sp_xray_energy.setValue(0)
        self.sp_detector_distance.setValue(0)
        self.sp_x_arr_size.setValue(0)
        self.sp_y_arr_size.setValue(0)
        self.sp_x_step_size.setValue(0)
        self.sp_y_step_size.setValue(0)
        self.sp_x_scan_range.setValue(0)
        self.sp_y_scan_range.setValue(0)
        #self.cb_scan_type = ...
        self.sp_num_points.setValue(0)

    
    def forceLoad(self):
        '''
        A foolproof mechanism that forces users to click "load" before "start" or "view data frame".
        This can avoid handling many weird exceptions.
        '''
        self._loaded = False


    def exception_handler(self, ex):
        formatted_lines = traceback.format_exc().splitlines()
        for line in formatted_lines:
            print("[ERROR] " + line, file=sys.stderr) 
        print("[ERROR] " + str(ex), file=sys.stderr)


    @QtCore.pyqtSlot(str, QtGui.QColor)
    def on_stdout_message(self, message, color):
        self.console_info.moveCursor(QtGui.QTextCursor.End)
        self.console_info.setTextColor(color)
        self.console_info.insertPlainText(message)


def main():
    app = QtWidgets.QApplication(sys.argv)

    w = MainWindow()
    w.show()
    app.installEventFilter(w)

    console_stdout = DPCStream(color = "black")
    console_stderr = DPCStream(color = "red")
    console_stdout.message.connect(w.on_stdout_message)
    console_stderr.message.connect(w.on_stdout_message)

    sys.stdout = console_stdout
    sys.stderr = console_stderr
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
