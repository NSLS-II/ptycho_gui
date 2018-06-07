# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_reconstep.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(680, 446)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.canvas_image = MplCanvas(self.centralwidget)
        self.canvas_image.setGeometry(QtCore.QRect(10, 50, 311, 291))
        self.canvas_image.setObjectName("canvas_image")
        self.canvas_metric = MplCanvas(self.centralwidget)
        self.canvas_metric.setGeometry(QtCore.QRect(340, 50, 311, 291))
        self.canvas_metric.setObjectName("canvas_metric")
        self.cb_image_kind = QtWidgets.QComboBox(self.centralwidget)
        self.cb_image_kind.setGeometry(QtCore.QRect(10, 20, 311, 27))
        self.cb_image_kind.setObjectName("cb_image_kind")
        self.cb_image_kind.addItem("")
        self.cb_image_kind.addItem("")
        self.cb_image_kind.addItem("")
        self.cb_image_kind.addItem("")
        self.cb_metric_kind = QtWidgets.QComboBox(self.centralwidget)
        self.cb_metric_kind.setGeometry(QtCore.QRect(340, 20, 311, 27))
        self.cb_metric_kind.setObjectName("cb_metric_kind")
        self.cb_metric_kind.addItem("")
        self.cb_metric_kind.addItem("")
        self.cb_metric_kind.addItem("")
        self.gridLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 350, 641, 80))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.progressBar = QtWidgets.QProgressBar(self.gridLayoutWidget)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout.addWidget(self.progressBar, 1, 0, 1, 1)
        self.sb_iter = QtWidgets.QSpinBox(self.gridLayoutWidget)
        self.sb_iter.setMinimum(1)
        self.sb_iter.setObjectName("sb_iter")
        self.gridLayout.addWidget(self.sb_iter, 0, 1, 1, 1)
        self.slider_iters = QtWidgets.QSlider(self.gridLayoutWidget)
        self.slider_iters.setMinimum(1)
        self.slider_iters.setOrientation(QtCore.Qt.Horizontal)
        self.slider_iters.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.slider_iters.setTickInterval(5)
        self.slider_iters.setObjectName("slider_iters")
        self.gridLayout.addWidget(self.slider_iters, 0, 0, 1, 1)
        self.cb_live = QtWidgets.QCheckBox(self.gridLayoutWidget)
        self.cb_live.setChecked(True)
        self.cb_live.setObjectName("cb_live")
        self.gridLayout.addWidget(self.cb_live, 0, 2, 1, 1)
        self.btn_close = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.btn_close.setObjectName("btn_close")
        self.gridLayout.addWidget(self.btn_close, 1, 1, 1, 2)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.cb_image_kind.setItemText(0, _translate("MainWindow", "object amplitude"))
        self.cb_image_kind.setItemText(1, _translate("MainWindow", "object phase"))
        self.cb_image_kind.setItemText(2, _translate("MainWindow", "probe amplitude"))
        self.cb_image_kind.setItemText(3, _translate("MainWindow", "probe phase"))
        self.cb_metric_kind.setItemText(0, _translate("MainWindow", "object chi"))
        self.cb_metric_kind.setItemText(1, _translate("MainWindow", "probe chi"))
        self.cb_metric_kind.setItemText(2, _translate("MainWindow", "diff chi"))
        self.cb_live.setText(_translate("MainWindow", "live"))
        self.btn_close.setText(_translate("MainWindow", "Close"))

from core.widgets.mplcanvas import MplCanvas
