# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_roi.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(540, 600)
        MainWindow.setMinimumSize(QtCore.QSize(452, 600))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.canvas = MplCanvasTool(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.canvas.sizePolicy().hasHeightForWidth())
        self.canvas.setSizePolicy(sizePolicy)
        self.canvas.setMinimumSize(QtCore.QSize(430, 400))
        self.canvas.setObjectName("canvas")
        self.verticalLayout.addWidget(self.canvas)
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setMinimumSize(QtCore.QSize(390, 140))
        self.groupBox.setMaximumSize(QtCore.QSize(16777215, 500))
        self.groupBox.setObjectName("groupBox")
        self.btn_save_to_h5 = QtWidgets.QPushButton(self.groupBox)
        self.btn_save_to_h5.setGeometry(QtCore.QRect(320, 100, 99, 27))
        self.btn_save_to_h5.setObjectName("btn_save_to_h5")
        self.doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.doubleSpinBox.setGeometry(QtCore.QRect(100, 70, 69, 27))
        self.doubleSpinBox.setObjectName("doubleSpinBox")
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(20, 80, 67, 17))
        self.label_2.setObjectName("label_2")
        self.widget = QtWidgets.QWidget(self.groupBox)
        self.widget.setGeometry(QtCore.QRect(10, 30, 502, 29))
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.btn_badpixels_brightest = QtWidgets.QPushButton(self.widget)
        self.btn_badpixels_brightest.setCheckable(True)
        self.btn_badpixels_brightest.setChecked(False)
        self.btn_badpixels_brightest.setObjectName("btn_badpixels_brightest")
        self.horizontalLayout.addWidget(self.btn_badpixels_brightest)
        self.btn_badpixels_outliers = QtWidgets.QPushButton(self.widget)
        self.btn_badpixels_outliers.setCheckable(True)
        self.btn_badpixels_outliers.setObjectName("btn_badpixels_outliers")
        self.horizontalLayout.addWidget(self.btn_badpixels_outliers)
        self.ck_show_badpixels = QtWidgets.QCheckBox(self.widget)
        self.ck_show_badpixels.setObjectName("ck_show_badpixels")
        self.horizontalLayout.addWidget(self.ck_show_badpixels)
        self.btn_badpixels_correct = QtWidgets.QPushButton(self.widget)
        self.btn_badpixels_correct.setEnabled(False)
        self.btn_badpixels_correct.setObjectName("btn_badpixels_correct")
        self.horizontalLayout.addWidget(self.btn_badpixels_correct)
        self.verticalLayout.addWidget(self.groupBox)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ROI "))
        self.groupBox.setTitle(_translate("MainWindow", "Tools"))
        self.btn_save_to_h5.setText(_translate("MainWindow", "save to h5"))
        self.label_2.setText(_translate("MainWindow", "threshold"))
        self.label.setText(_translate("MainWindow", "Bad pixels"))
        self.btn_badpixels_brightest.setText(_translate("MainWindow", "Brightest"))
        self.btn_badpixels_outliers.setText(_translate("MainWindow", "Outliers"))
        self.ck_show_badpixels.setText(_translate("MainWindow", "show bad pixels"))
        self.btn_badpixels_correct.setText(_translate("MainWindow", "Correct"))

from core.widgets.mplcanvastool import MplCanvasTool
