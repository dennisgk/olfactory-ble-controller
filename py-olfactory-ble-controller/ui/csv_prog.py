from PySide6 import QtCore, QtGui, QtWidgets

# for this one replace any resemblance of the iteration 1 and iteration 2 tabs AND size

class CsvProg(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 900)
        self.central_widget = QtWidgets.QWidget(MainWindow)
        self.central_widget.setObjectName("central_widget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.central_widget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.it_tabs = QtWidgets.QTabWidget(self.central_widget)
        self.it_tabs.setFocusPolicy(QtCore.Qt.NoFocus)
        self.it_tabs.setObjectName("it_tabs")
        self.verticalLayout_2.addWidget(self.it_tabs)
        self.export_button = QtWidgets.QPushButton(self.central_widget)
        self.export_button.setMinimumSize(QtCore.QSize(0, 41))
        self.export_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.export_button.setObjectName("export_button")
        self.verticalLayout_2.addWidget(self.export_button)
        MainWindow.setCentralWidget(self.central_widget)

        self.retranslateUi(MainWindow)
        self.it_tabs.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Olfactory Controller"))
        self.export_button.setText(_translate("MainWindow", "Export"))