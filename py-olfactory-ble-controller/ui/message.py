from PySide6 import QtCore, QtWidgets

class Message(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(300, 96)
        self.central_widget = QtWidgets.QWidget(MainWindow)
        self.central_widget.setObjectName("central_widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.central_widget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.central_widget)
        self.label.setMinimumSize(QtCore.QSize(0, 31))
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.okay_button = QtWidgets.QPushButton(self.central_widget)
        self.okay_button.setMinimumSize(QtCore.QSize(0, 41))
        self.okay_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.okay_button.setObjectName("okay_button")
        self.verticalLayout.addWidget(self.okay_button)
        MainWindow.setCentralWidget(self.central_widget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Olfactory Controller"))
        self.label.setText(_translate("MainWindow", "PLACEHOLDER"))
        self.okay_button.setText(_translate("MainWindow", "Okay"))