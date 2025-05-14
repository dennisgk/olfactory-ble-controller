from PySide6.QtCore import Signal, QThread

class QuitEvent():
    pass

class ControllerEvent():
    def __init__(self, callback):
        self.callback = callback

class BackgroundDispatchWorker(QThread):
    ev_update_ui = Signal(object)

    def __init__(self, controller):
        super().__init__(None)
        self.controller = controller

    def run(self):
        while True:
            ev = self.controller.wait_background_var()

            if type(ev) is ControllerEvent:
                self.ev_update_ui.emit(ev.callback)

            if type(ev) is QuitEvent:
                self.ev_update_ui.emit(lambda: self.controller.quit())
                break