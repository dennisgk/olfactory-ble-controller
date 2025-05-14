from . import Window
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt

class MainWindowView(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._running_csv_checked = False
        
        self.window.ui.running_csv_checkbox.stateChanged.connect(lambda: self.window.ui.running_csv_checkbox.setCheckState(Qt.Checked if self._running_csv_checked else Qt.Unchecked))

    def set_running_csv(self, val):
        self._running_csv_checked = val
        self.window.ui.start_csv_button.setEnabled(not self._running_csv_checked)
        self.window.ui.stop_csv_button.setEnabled(self._running_csv_checked)
        self.window.ui.running_csv_checkbox.setChecked(self._running_csv_checked)

    def get_running_csv(self):
        return self._running_csv_checked

    def add_relay(self, num, val):
        item = QListWidgetItem(f"Relay {num+1}")
        item.setCheckState(Qt.Checked if val else Qt.Unchecked)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setData(Qt.UserRole, num)
        self.window.ui.relays_list.addItem(item)

    def update_relays(self, vals):
        for item in [self.window.ui.relays_list.item(x) for x in range(0, self.window.ui.relays_list.count())]:
            item.setCheckState(Qt.Checked if vals[item.data(Qt.UserRole)] else Qt.Unchecked)

    def get_selected_relay_numbers(self):
        ret = []

        for x in self.window.ui.relays_list.selectedItems():
            ret.append(x.data(Qt.UserRole))

        return ret

class MainWindow(Window):
    def __init__(self, inst_class, parent=None):
        super().__init__(inst_class, parent)
        self.view = MainWindowView(self)