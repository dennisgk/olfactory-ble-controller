from . import Window
import csv
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QFileDialog

class CsvProgWindowView(QObject):
    def __init__(self, window, csv_prog_conv, safely_run, launch_message):
        super().__init__()
        self.window = window
        self._csv_prog_conv = csv_prog_conv
        self._launch_message = launch_message

        self._tabs_arr = []

        for num_it in set([x[0] for x in self._csv_prog_conv._saved_iteration_row_data]):
            self.add_iteration(num_it)
        
        for loc in self._csv_prog_conv._saved_iteration_row_data:
            self.render_row(loc[0], loc[1])

        it_handler = lambda num: safely_run(lambda: self.add_iteration(num))
        upd_handler = lambda it, row: safely_run(lambda: self.render_row(it, row))

        self._csv_prog_conv.add_handlers(it_handler, upd_handler)
        
        self.window.ev_close.connect(lambda: self._csv_prog_conv.remove_handlers(it_handler, upd_handler))
        self.window.ui.export_button.clicked.connect(self._export)

    def _save_export(self, file_path):
        if not file_path.endswith(".csv"):
            file_path = file_path + ".csv"

        with open(file_path, "w", newline="") as file:
            writer = csv.writer(file)

            headers = ["ITERATION"] + self._csv_prog_conv.get_headers()
            cols = 1 + len(headers)
            rows = self._csv_prog_conv.get_row_count()

            all_rows = [headers]

            for it in range(0, len(self._tabs_arr)):
                for row in range(0, rows):
                    row_inf = [f"{it+1}"]
                    for col in range(0, cols):
                        item = self._tabs_arr[it].item(row, col)
                        row_inf.append(item.text() if item else "")
                    all_rows.append(row_inf)

            writer.writerows(all_rows)

        self._launch_message("Successfully saved CSV file output", self.window)

    def _export(self):
        dialog = QFileDialog(self.window, "Save File As")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter("CSV Files (*.csv)")
        dialog.fileSelected.connect(self._save_export)
        dialog.show()

    def render_row(self, it, row):

        data = self._csv_prog_conv.get_row(it, row)
        for x in range(0, len(data)):
            self._tabs_arr[it].setItem(row, x, QTableWidgetItem(data[x]))

    def add_iteration(self, _num):

        cur_it = len(self._tabs_arr)

        tab = QWidget()
        tab.setFocusPolicy(Qt.NoFocus)
        tab.setObjectName(f"tab_{cur_it}")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setObjectName(f"tab_layout_{cur_it}")
        tab_table = QTableWidget(tab)
        tab_table.setFocusPolicy(Qt.NoFocus)
        tab_table.setRowCount(0)
        tab_table.setColumnCount(0)
        tab_table.setObjectName(f"tab_table_{cur_it}")
        tab_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(tab_table)

        headers = self._csv_prog_conv.get_headers()
        tab_table.setColumnCount(len(headers))
        tab_table.setHorizontalHeaderLabels(headers)

        tab_table.setRowCount(self._csv_prog_conv.get_row_count())

        self.window.ui.it_tabs.addTab(tab, f"Iteration {cur_it+1}")

        self._tabs_arr.append(tab_table)


class CsvProgWindow(Window):
    def __init__(self, inst_class, parent, csv_prog_conv, safely_run, launch_message):
        super().__init__(inst_class, parent)
        self.view = CsvProgWindowView(self, csv_prog_conv, safely_run, launch_message)