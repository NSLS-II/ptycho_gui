import sys
import os
from PyQt4 import QtGui, QtCore

from ui import ui_dpc
from core.dpc_param import Param
from core.dpc_recon import DPCReconWorker
from core.dpc_qt_utils import DPCStream

qt_connect = QtCore.QObject.connect
qt_signal = QtCore.SIGNAL

class MainWindow(QtGui.QMainWindow, ui_dpc.Ui_MainWindow):
    def __init__(self, parent=None, param:Param=None):
        super().__init__(parent)
        self.setupUi(self)
        QtGui.QApplication.setStyle('Plastique')

        #
        # connect
        #
        qt_connect(self.btn_recon_start, qt_signal('clicked()'), self.start)
        qt_connect(self.btn_recon_stop , qt_signal('clicked()'), self.stop)

        #
        # init.
        #
        if param is None:
            self.param = Param() # default
        else:
            self.param = param
        self._dpc_gpu_thread = None
        #self.update_gui_from_param()

    def update_param_from_gui(self):
        p = self.param
        p.scan_num = str(self.le_scan_num.text())
        p.sign = str(self.le_sign.text())
        p.n_iterations = int(self.sp_n_iterations.value())
        p.p_flag = self.ck_p_flag.isChecked()
        p.distance = float(self.sp_distance.value())
        p.mode_flag = self.ck_mode_flag.isChecked()
        p.gpu_flag = self.ck_gpu_flag.isChecked()
        p.mesh_flag = self.ck_mesh_flag.isChecked()
        p.start_ave = float(self.sp_start_ave.value())
        p.nth = int(self.sp_nth.value())
        p.ccd_pixel_um = float(self.sp_ccd_pixel_um.value())
        p.cal_scan_pattern_flag = self.ck_cal_scal_pattern_flag.isChecked()
        p.alg_flag = str(self.cb_alg_flag.currentText())
        p.ml_mode = str(self.cb_ml_mode.currentText())
        p.alg2_flag = str(self.cb_alg2_flag.currentText())
        p.alg_percentage = float(self.sp_alg_percentage.value())
        p.bragg_flag = self.ck_bragg_flag.isChecked()
        p.bragg_theta = float(self.sp_bragg_theta.value())
        p.bragg_gamma = float(self.sp_bragg_gamma.value())
        p.bragg_delta = float(self.sp_bragg_delta.value())
        p.amp_max = float(self.sp_amp_max.value())
        p.amp_min = float(self.sp_amp_min.value())
        p.pha_max = float(self.sp_pha_max.value())
        p.pha_min = float(self.sp_pha_min.value())
        p.pc_flag = self.ck_pc_flag.isChecked()
        p.pc_sigma = float(self.sp_pc_sigma.value())
        p.pc_alg = str(self.cb_pc_alg.currentText())
        p.pc_kernel_n = int(self.sp_pc_kernel_n.value())
        p.alpha = float(self.sp_alpha.value())
        p.beta = float(self.sp_beta.value())
        p.save_tmp_pic_flag = self.ck_save_tmp_pic_flag.isChecked()
        p.prb_mode_num = int(self.sp_prb_mode_num.value())
        p.obj_mode_num = int(self.sp_obj_mode_num.value())
        p.position_correction_flag = self.ck_position_correction_flag.isChecked()
        p.position_correction_start = int(self.sp_position_correction_start.value())
        p.position_correction_step = int(self.sp_position_correction_step.value())
        p.multislice_flag = self.ck_multislice_flag.isChecked()
        p.slice_num = int(self.sp_slice_num.value())
        p.slice_spacing_m = float(self.sp_slice_spacing_m.value())
        p.start_update_probe = int(self.sp_start_update_probe.value())
        p.start_update_object = int(self.sp_start_update_object.value())
        p.init_obj_flag = self.ck_init_obj_flag.isChecked()
        p.init_obj_dpc_flag = self.ck_init_obj_dpc_flag.isChecked()
        p.prb_center_flag = self.ck_prb_center_flag.isChecked()
        p.init_prb_flag = self.ck_init_prb_flag.isChecked()
        p.mask_prb_flag = self.ck_mask_prb_flag.isChecked()
        p.dm_version = int(self.sp_dm_version.value())
        p.sf_flag = self.ck_sf_flag.isChecked()
        p.ms_pie_flag = self.ck_ms_pie_flag.isChecked()
        p.weak_obj_flag = self.ck_weak_obj_flag.isChecked()
        p.processes = int(self.sp_processes.value())

    def update_gui_from_param(self):
        p = self.param
        self.le_scan_num.setText(p.scan_num)
        self.le_sign.setText(p.sign)
        self.sp_n_iterations.setValue(p.n_iterations)
        self.ck_p_flag.setChecked(p.p_flag)
        self.sp_distance.setValue(p.distance)
        self.ck_mode_flag.setChecked(p.mode_flag)
        self.ck_gpu_flag.setChecked(p.gpu_flag)
        self.ck_mesh_flag.setChecked(p.mesh_flag)
        self.sp_start_ave.setValue(p.start_ave)
        self.sp_nth.setValue(p.nth)
        self.sp_ccd_pixel_um.setValue(p.ccd_pixel_um)
        self.ck_cal_scal_pattern_flag.setChecked(p.cal_scan_pattern_flag)
        self.cb_alg_flag.setCurrentIndex(p.get_alg_flg_index())
        self.cb_ml_mode.setCurrentIndex(p.get_ml_model_index())
        self.cb_alg2_flag.setCurrentIndex(p.get_alg2_flg_index())
        self.sp_alg_percentage.setValue(p.alg_percentage)
        self.ck_bragg_flag.setChecked(p.bragg_flag)
        self.sp_bragg_theta.setValue(p.bragg_theta)
        self.sp_bragg_gamma.setValue(p.bragg_gamma)
        self.sp_bragg_delta.setValue(p.bragg_delta)
        self.sp_amp_max.setValue(p.amp_max)
        self.sp_amp_min.setValue(p.amp_min)
        self.sp_pha_max.setValue(p.pha_max)
        self.sp_pha_min.setValue(p.pha_min)
        self.ck_pc_flag.setChecked(p.pc_flag)
        self.sp_pc_sigma.setValue(p.pc_sigma)
        self.cb_pc_alg.setCurrentIndex(p.get_pc_alg_index())
        self.sp_pc_kernel_n.setValue(p.pc_kernel_n)
        self.sp_alpha.setValue(p.alpha)
        self.sp_beta.setValue(p.beta)
        self.ck_save_tmp_pic_flag.setChecked(p.save_tmp_pic_flag)
        self.sp_prb_mode_num.setValue(p.prb_mode_num)
        self.sp_obj_mode_num.setValue(p.obj_mode_num)
        self.ck_position_correction_flag.setChecked(p.position_correction_flag)
        self.sp_position_correction_start.setValue(p.position_correction_start)
        self.sp_position_correction_step.setValue(p.position_correction_step)
        self.ck_multislice_flag.setChecked(p.multislice_flag)
        self.sp_slice_num.setValue(p.slice_num)
        self.sp_slice_spacing_m.setValue(p.slice_spacing_m)
        self.sp_start_update_probe.setValue(p.start_update_probe)
        self.sp_start_update_object.setValue(p.start_update_object)
        self.ck_init_obj_flag.setChecked(p.init_obj_flag)
        self.ck_init_obj_dpc_flag.setChecked(p.init_obj_dpc_flag)
        self.ck_prb_center_flag.setChecked(p.prb_center_flag)
        self.ck_init_prb_flag.setChecked(p.init_prb_flag)
        self.ck_mask_prb_flag.setChecked(p.mask_prb_flag)
        self.sp_dm_version.setValue(p.dm_version)
        self.ck_sf_flag.setChecked(p.sf_flag)
        self.ck_ms_pie_flag.setChecked(p.ms_pie_flag)
        self.ck_weak_obj_flag.setChecked(p.weak_obj_flag)
        self.sp_processes.setValue(p.processes)

    def start(self):
        if self._dpc_gpu_thread is not None and self._dpc_gpu_thread.isFinished():
            self._dpc_gpu_thread = None

        if self._dpc_gpu_thread is None:
            self.recon_bar.setValue(0)
            self.recon_bar.setMaximum(self.param.n_iterations)
            self.update_param_from_gui()

            thread = self._dpc_gpu_thread = DPCReconWorker(self.param)
            thread.update_signal.connect(self.update_recon_step)
            thread.start()

    def stop(self):
        pass

    def update_recon_step(self, it):
        self.recon_bar.setValue(it)

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