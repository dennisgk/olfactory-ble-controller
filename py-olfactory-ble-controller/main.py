from PySide6.QtWidgets import QApplication
import sys
from sync_waiter import SyncWaiter
from background_dispatch_worker import BackgroundDispatchWorker, QuitEvent, ControllerEvent
from window import Window
from window.main_window import MainWindow
from window.csv_select_window import CsvSelectWindow
from window.csv_prog_window import CsvProgWindow
from ui.loader import Loader
from ui.select import Select
from ui.main import Main
from ui.message import Message
from ui.csv_select import CsvSelect
from ui.csv_prog import CsvProg
from proc_pipeline import start_program

class PyOlfactoryBleController:
    def _acct_window(self, window):
        self._add_active_window(window)
        window.ev_close.connect(lambda: self._remove_active_window(window))

    def _launch_loader(self, label):
        loader_window = Window(Loader)
        self._acct_window(loader_window)
        loader_window.ui.label.setText(label)
        loader_window.show()

        return loader_window

    def _launch_select(self, label):
        select_window = Window(Select)
        self._acct_window(select_window)
        select_window.ui.label.setText(label)
        select_window.show()

        return select_window

    def _launch_message(self, label, parent):
        message_window = Window(Message, parent)
        # has parent so no acct
        message_window.ui.label.setText(label)
        message_window.ui.okay_button.clicked.connect(lambda: message_window.close())
        message_window.show()

        return message_window
        
    def _launch_main(self):
        main_window = MainWindow(Main)
        self._acct_window(main_window)
        main_window.show()

        return main_window
    
    def _launch_csv_select(self, parent):
        csv_select_window = CsvSelectWindow(CsvSelect, parent)
        # has parent so no acct
        csv_select_window.show()

        return csv_select_window
    
    def _launch_csv_prog(self, parent, csv_prog_conv):
        csv_prog_window = CsvProgWindow(CsvProg, parent, csv_prog_conv, lambda x: self._background_loop.set(ControllerEvent(x)), self._launch_message)
        # has parent so no acct
        csv_prog_window.show()

        return csv_prog_window
    
    def quit(self):
        self._background_loop.quit()
        self._app.quit()

    def wait_background_var(self):
        return self._background_loop.wait_var()
    
    def _init_active_windows(self):
        self._active_windows = []

    def _add_active_window(self, window):
        self._active_windows.append(window)

    def _quit_if_needed(self):
        if len(self._active_windows) == 0 and self._background_loop.len_var_queue() == 0 and self._background_loop.len_downtime_var_queue() == 0:
            self._background_loop.set(QuitEvent())

    def _remove_active_window(self, window):
        self._active_windows.remove(window)
        self._quit_if_needed()

    def __init__(self, argv):
        self._app = QApplication(argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._init_active_windows()
        self._background_loop = SyncWaiter()

        self._background_worker = BackgroundDispatchWorker(self)
        self._background_worker.ev_update_ui.connect(lambda x: x())
        self._background_worker.start()

        self._on_quit = lambda: None

    def exec(self):
        ret_val = self._app.exec()
        self._background_worker.wait()
        self._on_quit()

        return ret_val

if __name__ == "__main__":
    controller = PyOlfactoryBleController(sys.argv)
    
    start_program(controller)
    sys.exit(controller.exec())
