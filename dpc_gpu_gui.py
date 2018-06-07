import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog

from ui import ui_dpc
from core.dpc_param import Param
from core.dpc_recon import DPCReconWorker, DPCReconFakeWorker
from core.dpc_qt_utils import DPCStream

from reconStep_gui import ReconStepWindow

import h5py
import numpy as np
from numpy.lib.format import open_memmap
import matplotlib.pyplot as plt



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
        self.btn_load_scan.clicked.connect(self.loadExpParam)

        self.ck_mode_flag.clicked.connect(self.updateModeFlg)
        self.ck_multislice_flag.clicked.connect(self.updateMultiSliceFlg)
        self.ck_gpu_flag.clicked.connect(self.updateGpuFlg)

        self.btn_recon_start.clicked.connect(self.start)
        self.btn_recon_stop.clicked.connect(self.stop)

        self.btn_gpu_all = [self.btn_gpu_0, self.btn_gpu_1, self.btn_gpu_2, self.btn_gpu_3]

        # init.
        if param is None:
            self.param = Param() # default
        else:
            self.param = param
        self._prb = None
        self._obj = None
        self._dpc_gpu_thread = None

        self.reconStepWindow = None

        self.update_gui_from_param()
        self.updateModeFlg()
        self.updateMultiSliceFlg()
        self.updateGpuFlg()
        self.resetButtons()
        self.resetExperimentalParameters() # probably not necessary



    def resetButtons(self):
        self.btn_recon_start.setEnabled(True)
        self.btn_recon_stop.setEnabled(False)
        self.recon_bar.setValue(0)
        plt.ioff()
        plt.close('all')
        # close the mmap arrays
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
        p.frame_num = int(self.sp_fram_num.value())

        p.xray_energy = float(self.sp_xray_energy.value()) # do we need this one?
        p.z_m = float(self.sp_detector_distance.value())
        #p.x_arr_size = float(self.sp_x_arr_size.value()) # can get from diffamp
        p.dr_x = float(self.sp_x_step_size.value())
        p.x_range = float(self.sp_x_scan_range.value())
        #p.y_arr_size = float(self.sp_y_arr_size.value()) # can get from diffamp
        p.dr_y = float(self.sp_y_step_size.value())
        p.y_range = float(self.sp_y_scan_range.value())
        p.scan_type = str(self.cb_scan_type.currentText()) # do we need this one?
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

        p.alpha = float(self.sp_alpha.value()*1.e-8)
        p.beta = float(self.sp_beta.value())

        p.display_interval = int(self.sp_display_interval.value())


    def update_gui_from_param(self):
        p = self.param
        self.le_scan_num.setText(p.scan_num)
        self.le_sign.setText(p.sign)
        self.cb_detectorkind.setCurrentIndex(p.get_detector_kind_index())
        self.sp_fram_num.setValue(int(p.frame_num))

        self.sp_xray_energy.setValue(float(p.xray_energy))
        self.sp_detector_distance.setValue(float(p.detector_distance))
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

        self.sp_alpha.setValue(p.alpha * 1e+8)
        self.sp_beta.setValue(p.beta)

        self.sp_display_interval.setValue(p.display_interval)


    def start(self):
        # -------------------- Sungsoo version -------------------------------------
        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isFinished():
            self._dpc_gpu_thread = None

        if self._dpc_gpu_thread is None:
            # init reconStepWindow
            if self.reconStepWindow is None:
                self.reconStepWindow = ReconStepWindow()
                self.reconStepWindow.reset_iter(self.param.n_iterations)
                self.reconStepWindow.show()

            self.update_param_from_gui()
            self.recon_bar.setValue(0)
            self.recon_bar.setMaximum(self.param.n_iterations)

            thread = self._dpc_gpu_thread = DPCReconFakeWorker(self.param)
            thread.update_signal.connect(self.update_recon_step)
            thread.finished.connect(self.resetButtons)
            thread.start()

            self.btn_recon_stop.setEnabled(True)
            self.btn_recon_start.setEnabled(False)
        # -------------------- Leo version -------------------------------------
        # if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isFinished():
        #     self._dpc_gpu_thread = None
        #
        # if self._dpc_gpu_thread is None:
        #     self.update_param_from_gui()
        #     self.recon_bar.setValue(0)
        #     self.recon_bar.setMaximum(self.param.n_iterations)
        #
        #     # TEST: get live update of probe and object
        #     # the order of these two lines cannot be exchanged!
        #     plt.ion() # non-blocking plotting
        #     plt.figure()
        #     if self.param.gpu_flag and self.param.display_interval<3:
        #         print("[WARNING] The display interval is too small ({}). You might not see the actual live update."\
        #               .format(self.param.display_interval), file=sys.stderr)
        #
        #     thread = self._dpc_gpu_thread = DPCReconWorker(self.param)
        #     thread.update_signal.connect(self.update_recon_step)
        #     thread.finished.connect(self.resetButtons)
        #     thread.start()
        #
        #     self.btn_recon_stop.setEnabled(True)
        #     self.btn_recon_start.setEnabled(False)


    def stop(self):
        # -------------------- Sungsoo version -------------------------------------
        # close reconStepWindow ??? (or close from reconStepWindow)
        if self.reconStepWindow is not None:
            self.reconStepWindow.close()

        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isRunning():
            self._dpc_gpu_thread.quit()
            self._dpc_gpu_thread = None
            self.resetButtons()
        # -------------------- Leo version -------------------------------------
        # force quitting if running, otherwise do nothing
        # if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isRunning():
        #     self._dpc_gpu_thread.kill() # first kill the mpi processes
        #     self._dpc_gpu_thread.quit() # then quit QThread gracefully
        #     self._dpc_gpu_thread = None
        #     self.resetButtons()


    def update_recon_step(self, it):
        self.recon_bar.setValue(it)

        # -------------------- Sungsoo version -------------------------------------
        if self.reconStepWindow is not None:
            self.reconStepWindow.update_iter(it)

            # a list of random images for test
            images = [np.random.random((128,128)) for _ in range(4)]
            self.reconStepWindow.update_images(it, images)

        # -------------------- Leo version -------------------------------------
        # TEST: get live update of probe and object
        # try:
        #     it -= 1
        #     if it == 0:
        #         # the two npy are created by ptycho by this time
        #         self._prb = open_memmap(self.param.working_directory + '.mmap_prb.npy', mode = 'r')
        #         self._obj = open_memmap(self.param.working_directory + '.mmap_obj.npy', mode = 'r')
        #     if it % self.param.display_interval == 1 or (it > 0 and self.param.display_interval == 1):
        #         # look at the previous slice to mitigate synchronization problem? should have better solution...
        #         plt.clf()
        #         plt.subplot(221)
        #         plt.imshow(np.flipud(np.abs(self._prb[it-1, 0]).T))
        #         plt.colorbar()
        #         plt.subplot(222)
        #         plt.imshow(np.flipud(np.angle(self._prb[it-1, 0]).T))
        #         plt.colorbar()
        #         plt.subplot(223)
        #         plt.imshow(np.flipud(np.abs(self._obj[it-1, 0]).T))
        #         plt.colorbar()
        #         plt.subplot(224)
        #         plt.imshow(np.flipud(np.angle(self._obj[it-1, 0]).T))
        #         plt.colorbar()
        #         plt.suptitle('iteration #'+str(it-1))
        #         plt.show()
        # except Exception as ex:
        #     print(ex, file=sys.stderr)


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


    def viewDataFrame(self):
        '''
        Correspond to "View & set" in DPC GUI
        '''
        pass


    def loadExpParam(self): 
        '''
        WARNING:
        Currently this function only supports h5.
        '''
        if self.cb_dataloader.currentText() == "Load from databroker":
            # do nothing because databroker is not ready
            print("[ERROR] the databroker is currently unavailable in this version.", file=sys.stderr)
            self.resetExperimentalParameters()

        # load the parameters from the h5 in the working directory
        if self.cb_dataloader.currentText() == "Load from h5":
            working_dir = str(self.le_working_directory.text()) # self.param.working_directory
            scan_num = str(self.le_scan_num.text())
            try:
                with h5py.File(working_dir+'/scan_'+scan_num+'.h5','r') as f:
                    # this code is not robust enough as certain keys may not be present...
                    print("h5 loaded, parsing experimental parameters...", end='')
                    self.sp_xray_energy.setValue(1.24/f['lambda_nm'].value)
                    self.sp_detector_distance.setValue(f['z_m'].value)
                    nz, nx, ny = f['diffamp'].shape
                    self.sp_x_arr_size.setValue(nx)
                    self.sp_y_arr_size.setValue(ny)
                    self.sp_x_step_size.setValue(f['dr_x'].value)
                    self.sp_y_step_size.setValue(f['dr_y'].value)
                    self.sp_x_scan_range.setValue(f['x_range'].value)
                    self.sp_y_scan_range.setValue(f['y_range'].value)
                    #self.cb_scan_type = ...
                    self.sp_num_points.setValue(nz)
                    print("done")
            except OSError:
                print("[ERROR] h5 not found. Resetting...", file=sys.stderr, end='')
                self.resetExperimentalParameters()
                print("done", file=sys.stderr)


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
