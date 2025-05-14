from . import Window
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog
from pydantic import BaseModel

class CsvSelectRun(BaseModel):
    file_path: str

class CsvSelectIterationsRun(CsvSelectRun):
    iterations: int

class CsvSelectWindowView(QObject):
    ev_submit = Signal(CsvSelectRun)

    def __init__(self, window):
        super().__init__()
        self.window = window

        self._combo_items = ["Run For Iterations", "Run Perpetually"]
        self._file_path = None

        self.window.ui.run_type_combo.addItems(self._combo_items)
        self.window.ui.run_type_combo.currentIndexChanged.connect(self._on_combo_index)
        self._on_combo_index(0)

        self.window.ui.okay_button.clicked.connect(self._on_okay)
        self.window.ui.select_csv_button.clicked.connect(self._select_csv)

    def _select_csv(self):
        dialog = QFileDialog(self.window)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("CSV Files (*.csv)")
        dialog.fileSelected.connect(self._set_file_path)
        dialog.show()

    def _set_file_path(self, file_path):
        self._file_path = file_path
        self.window.ui.csv_path_label.setText(self._file_path)

    def _on_combo_index(self, index):
        if index == 0:
            self.window.ui.iterations_spin.show()
        else:
            self.window.ui.iterations_spin.hide()

    def _on_okay(self):
        if self.window.ui.run_type_combo.currentIndex() == 0:
            self.ev_submit.emit(CsvSelectIterationsRun(file_path=self._file_path, iterations=self.window.ui.iterations_spin.value()))
        else:
            self.ev_submit.emit(CsvSelectRun(file_path=self._file_path))

        self.window.close()

class CsvSelectWindow(Window):
    def __init__(self, inst_class, parent):
        super().__init__(inst_class, parent)
        self.view = CsvSelectWindowView(self)