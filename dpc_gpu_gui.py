import sys
import os
from PyQt4 import QtGui, QtCore

from ui import ui_dpc
from core.dpc_param import Param
from core.dpc_recon import DPCReconWorker
from core.dpc_qt_utils import DPCStream

import h5py


class MainWindow(QtGui.QMainWindow, ui_dpc.Ui_MainWindow):
    def __init__(self, parent=None, param:Param=None):
        super().__init__(parent)
        self.setupUi(self)
        QtGui.QApplication.setStyle('Plastique')

        # connect
        QtCore.QObject.connect(self.btn_load_probe , QtCore.SIGNAL('clicked()'), self.loadProbe)
        QtCore.QObject.connect(self.btn_load_object, QtCore.SIGNAL('clicked()'), self.loadObject)
        QtCore.QObject.connect(self.ck_init_prb_flag, QtCore.SIGNAL('clicked()'), self.updateProbeFlg)
        QtCore.QObject.connect(self.ck_init_obj_flag, QtCore.SIGNAL('clicked()'), self.updateObjectFlg)

        QtCore.QObject.connect(self.btn_choose_cwd, QtCore.SIGNAL('clicked()'), self.setWorkingDirectory)
        QtCore.QObject.connect(self.btn_view_frame, QtCore.SIGNAL('clicked()'), self.viewDataFrame)

        QtCore.QObject.connect(self.ck_mode_flag, QtCore.SIGNAL('clicked()'), self.updateModeFlg)
        QtCore.QObject.connect(self.ck_multislice_flag, QtCore.SIGNAL('clicked()'), self.updateMultiSliceFlg)
        QtCore.QObject.connect(self.ck_gpu_flag, QtCore.SIGNAL('clicked()'), self.updateGpuFlg)

        QtCore.QObject.connect(self.btn_recon_start, QtCore.SIGNAL('clicked()'), self.start)
        QtCore.QObject.connect(self.btn_recon_stop , QtCore.SIGNAL('clicked()'), self.stop)

        self.btn_gpu_all = [self.btn_gpu_0, self.btn_gpu_1, self.btn_gpu_2, self.btn_gpu_3]

        # init.
        if param is None:
            self.param = Param() # default
        else:
            self.param = param
        self._dpc_gpu_thread = None
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
        

    def update_param_from_gui(self):
        p = self.param
        p.scan_num = str(self.le_scan_num.text())
        p.sign = str(self.le_sign.text())
        p.detectorkind = str(self.cb_detectorkind.currentText())
        p.frame_num = int(self.sp_fram_num.value())

        p.xray_energy = float(self.sp_xray_energy.value())
        p.detector_distance = float(self.sp_detector_distance.value())
        p.x_arr_size = float(self.sp_x_arr_size.value())
        p.x_step_size = float(self.sp_x_step_size.value())
        p.x_scan_range = float(self.sp_x_scan_range.value())
        p.y_arr_size = float(self.sp_y_arr_size.value())
        p.y_step_size = float(self.sp_y_step_size.value())
        p.y_scan_range = float(self.sp_y_scan_range.value())
        p.scan_type = str(self.cb_scan_type.currentText())
        p.num_points = int(self.sp_num_points.value())

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

        self.sp_amp_max.setValue(float(p.amp_max))
        self.sp_amp_min.setValue(float(p.amp_min))
        self.sp_pha_max.setValue(float(p.pha_max))
        self.sp_pha_min.setValue(float(p.pha_min))

        self.ck_gpu_flag.setChecked(p.gpu_flag)
        for btn_gpu, id in zip(self.btn_gpu_all, range(len(self.btn_gpu_all))):
            btn_gpu.setChecked(id in p.gpus)


    def start(self):
        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isFinished():
            self._dpc_gpu_thread = None

        if self._dpc_gpu_thread is None:
            self.recon_bar.setValue(0)
            self.recon_bar.setMaximum(self.param.n_iterations)
            self.update_param_from_gui()

            thread = self._dpc_gpu_thread = DPCReconWorker(self.param)
            thread.update_signal.connect(self.update_recon_step)
            QtCore.QObject.connect(thread, QtCore.SIGNAL("finished()"), self.resetButtons)
            thread.start()

            self.btn_recon_stop.setEnabled(True)
            self.btn_recon_start.setEnabled(False)


    def stop(self):
        # force quitting if running, otherwise do nothing
        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isRunning():
        #if self._dpc_gpu_thread is not None:
            self._dpc_gpu_thread.kill() # first kill the mpi processes
            self._dpc_gpu_thread.quit() # then quit QThread gracefully
            #self._dpc_gpu_thread.terminate()
            #self._dpc_gpu_thread.wait()
            self._dpc_gpu_thread = None
            self.resetButtons()


    def update_recon_step(self, it):
        self.recon_bar.setValue(it)


    def loadProbe(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open probe file', filter="(*.npy)")
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
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open object file', filter="(*.npy)")
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
        dirname = QtGui.QFileDialog.getExistingDirectory(self, 'Choose working folder', directory=os.path.expanduser("~"))
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
        WARNING:
        Currently this function only fetches experimental paramters from h5 and does nothing more.
        But in the future we would like to add the visualization here.
        '''
        if self.cb_dataloader.currentText() == "Load from databroker":
            # do nothing because databroker is not ready
            print("\033[1;33mERROR\033[0m [ERROR] the databroker is currently unavailable in this version.", file=sys.stderr)
            self.resetExperimentalParameters()

        # load the parameters from the h5 in the working directory
        if self.cb_dataloader.currentText() == "Load from h5":
            working_dir = str(self.le_working_directory.text()) # self.param.working_directory
            scan_num = str(self.le_scan_num.text())
            try:
                with h5py.File(working_dir+'/scan_'+scan_num+'.h5','r') as f:
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
            except OSError:
                print("[ERROR] h5 not found...", file=sys.stderr, end='')
                self.resetExperimentalParameters()
            finally:
                print("done")


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


    @QtCore.pyqtSlot(str)
    def on_stdout_message(self, message):
        self.console_info.moveCursor(QtGui.QTextCursor.End)
        self.console_info.insertPlainText(message)


def main():
    app = QtGui.QApplication(sys.argv)

    w = MainWindow()
    w.show()
    app.installEventFilter(w)

    console_out = DPCStream()
    console_out.message.connect(w.on_stdout_message)

    sys.stdout = console_out
    sys.stderr = console_out
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
