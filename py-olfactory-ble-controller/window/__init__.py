from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Signal
from qt_material import QtStyleTools

class Window(QMainWindow, QtStyleTools):
    ev_close = Signal(object)

    def __init__(self, inst_class, parent=None):
        super().__init__(parent=parent)
        self.ui = inst_class()
        self.ui.setupUi(self)
        self.apply_stylesheet(self.centralWidget(), "dark_teal.xml")
        
    def closeEvent(self, event):
        self.ev_close.emit(event)
