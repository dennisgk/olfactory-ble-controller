from PySide6 import QtCore, QtWidgets

class Select(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(300, 200)
        self.central_widget = QtWidgets.QWidget(MainWindow)
        self.central_widget.setObjectName("central_widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.central_widget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.central_widget)
        self.label.setMinimumSize(QtCore.QSize(0, 31))
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.list_widget = QtWidgets.QListWidget(self.central_widget)
        self.list_widget.setObjectName("list_widget")
        self.verticalLayout.addWidget(self.list_widget)
        self.select_button = QtWidgets.QPushButton(self.central_widget)
        self.select_button.setMinimumSize(QtCore.QSize(0, 41))
        self.select_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.select_button.setObjectName("select_button")
        self.verticalLayout.addWidget(self.select_button)
        MainWindow.setCentralWidget(self.central_widget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Olfactory Controller"))
        self.label.setText(_translate("MainWindow", "PLACEHOLDER"))
        self.select_button.setText(_translate("MainWindow", "Select"))