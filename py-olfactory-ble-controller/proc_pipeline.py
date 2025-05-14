from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt, QThread
import simplepyble
from background_dispatch_worker import ControllerEvent
import threading
from ble_dev import CsvProgConv, gen_command_get_csv_cur_state_bytes, gen_command_get_csv_prog_bytes, dev_COMMAND_GET_CSV_PROG, dev_COMMAND_GET_CSV_CUR_STAT, dev_char_notify_csv, dev_command_csv_block_size, dev_COMMAND_GET_RELAYS, dev_COMMAND_GET_CSV_ACTIVE, gen_command_start_csv, dev_search_millis, dev_name, dev_num_relays, dev_char_csv, dev_char_notify, dev_char_write, gen_command_get_relays_bytes, gen_command_get_csv_active_bytes, conv_get_csv_active_data, conv_get_relays_data, gen_command_alter_disable, gen_command_alter_enable, gen_command_csv_stop
from window.csv_select_window import CsvSelectIterationsRun, CsvSelectRun

# we will allow private variable access on controller only in this file
# allow private variable access on the windows too

# call controller._quit_if_needed() when ending a thr that may not spawn a window maybe?

class NotifyHandler():
    def __init__(self, peripheral, uuid_pair_notify, uuid_pair_notify_csv):
        peripheral.notify(*uuid_pair_notify, self._on_data)
        peripheral.notify(*uuid_pair_notify_csv, self._on_csv_data)
        self._att_comm_listeners = {}
        self._csv_notify_callback = lambda _: None

    def attach_listener_command(self, command, handler):
        self._att_comm_listeners.update(dict([(command, handler)]))

    def attach_listener_command_once(self, command, handler):
        def act_handler(data):
            handler(data)
            self._att_comm_listeners.pop(command)

        self._att_comm_listeners.update(dict([(command, act_handler)]))

    def attach_csv_notify_listener(self, handler):
        self._csv_notify_callback = handler

    def _on_data(self, data):
        if(len(data) == 0):
            return
        
        if data[0] in self._att_comm_listeners.keys():
            self._att_comm_listeners.get(data[0])(data)

    def _on_csv_data(self, data):
        self._csv_notify_callback(data)

def start_program(controller):
    controller._background_loop.set(ControllerEvent(lambda: adapter_choice_pipeline(controller)))

def adapter_choice_pipeline(controller):
    adapters = simplepyble.Adapter.get_adapters()

    select_window = controller._launch_select("Select your adapter:")
    for i, adapter in enumerate(adapters):
        item = QListWidgetItem(f"{i+1}: {adapter.identifier()} [{adapter.address()}]")
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setData(Qt.UserRole, adapter)
        select_window.ui.list_widget.addItem(item)

    def on_select():
        if len(select_window.ui.list_widget.selectedItems()) != 1:
            return
        
        adapter = select_window.ui.list_widget.selectedItems()[0].data(Qt.UserRole)
        ble_dev_load_pipeline(controller, adapter)
        select_window.close()

    select_window.ui.select_button.clicked.connect(on_select)

def ble_dev_load_pipeline(controller, adapter):
    loader_window = controller._launch_loader("Searching for devices...")

    def search():
        adapter.scan_for(dev_search_millis)
        unclean_peripherals = adapter.scan_get_results()
        peripherals = [x for x in unclean_peripherals if x.identifier() == dev_name]

        def on_load():
            ble_dev_choice_pipeline(controller, adapter, peripherals)
            loader_window.close()

        controller._background_loop.set(ControllerEvent(on_load))

    search_thr = threading.Thread(target=search)
    search_thr.start()

def ble_dev_choice_pipeline(controller, adapter, peripherals):
    select_window = controller._launch_select("Select your device:")
    for i, peripheral in enumerate(peripherals):
        item = QListWidgetItem(f"{i+1}: {peripheral.identifier()} [{peripheral.address()}]")
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setData(Qt.UserRole, peripheral)
        select_window.ui.list_widget.addItem(item)

    def on_select():
        if len(select_window.ui.list_widget.selectedItems()) != 1:
            return
        
        peripheral = select_window.ui.list_widget.selectedItems()[0].data(Qt.UserRole)
        ble_dev_main_load_pipeline(controller, peripheral)
        select_window.close()

    select_window.ui.select_button.clicked.connect(on_select)

def ble_dev_main_load_pipeline(controller, peripheral):
    loader_window = controller._launch_loader("Connecting to peripheral...")

    def connect():
        try:
            peripheral.connect()
        except:
            def fail_launch():
                message_window = controller._launch_message("Error - Failed to connect to peripheral.", loader_window)
                message_window.ev_close.connect(lambda: loader_window.close())

            controller._background_loop.set(ControllerEvent(fail_launch))
            return

        controller._on_quit = lambda: peripheral.disconnect()

        services = peripheral.services()

        uuid_pair_notify = None
        uuid_pair_notify_csv = None
        uuid_pair_write = None
        uuid_pair_csv = None

        for service in services:
            for characteristic in service.characteristics():
                char_uuid = characteristic.uuid().lower()

                if dev_char_notify in char_uuid:
                    uuid_pair_notify = [service.uuid(), characteristic.uuid()]

                if dev_char_notify_csv in char_uuid:
                    uuid_pair_notify_csv = [service.uuid(), characteristic.uuid()]

                if dev_char_write in char_uuid:
                    uuid_pair_write = [service.uuid(), characteristic.uuid()]

                if dev_char_csv in char_uuid:
                    uuid_pair_csv = [service.uuid(), characteristic.uuid()]

        notify_handler = NotifyHandler(peripheral, uuid_pair_notify, uuid_pair_notify_csv)

        def on_get_relays_info(relays_data):

            def on_get_csv_info(csv_active_data):

                csv_cur_file = CsvProgConv()

                def on_get_csv_file(csv_file_inf):
                    
                    csv_cur_file.catch_header(csv_file_inf)

                    def on_get_csv_last_stat(csv_last_stat):
                        
                        csv_cur_file.catch_update(csv_last_stat)
                        
                        def on_load():
                            ble_dev_main_pipeline(controller, peripheral, notify_handler, uuid_pair_write, uuid_pair_csv, conv_get_relays_data(relays_data), conv_get_csv_active_data(csv_active_data), csv_cur_file)
                            loader_window.close()

                        controller._background_loop.set(ControllerEvent(on_load))

                    notify_handler.attach_listener_command_once(dev_COMMAND_GET_CSV_CUR_STAT, on_get_csv_last_stat)
                    peripheral.write_request(*uuid_pair_write, gen_command_get_csv_cur_state_bytes())

                notify_handler.attach_listener_command_once(dev_COMMAND_GET_CSV_PROG, on_get_csv_file)
                notify_handler.attach_csv_notify_listener(lambda data: csv_cur_file.catch_csv(data))
                peripheral.write_request(*uuid_pair_write, gen_command_get_csv_prog_bytes())

            notify_handler.attach_listener_command_once(dev_COMMAND_GET_CSV_ACTIVE, on_get_csv_info)
            peripheral.write_request(*uuid_pair_write, gen_command_get_csv_active_bytes())

        notify_handler.attach_listener_command_once(dev_COMMAND_GET_RELAYS, on_get_relays_info)
        peripheral.write_request(*uuid_pair_write, gen_command_get_relays_bytes())
    
    connect_thr = threading.Thread(target=connect)
    connect_thr.start()

def ble_dev_main_pipeline(controller, peripheral, notify_handler, uuid_pair_write, uuid_pair_csv, init_relays, init_csv_active, init_csv_saved_data):
    main_window = controller._launch_main()

    for i in range(0, dev_num_relays):
        main_window.view.add_relay(i, init_relays[i])

    main_window.view.set_running_csv(init_csv_active)

    csv_saved_data = [] if init_csv_saved_data.is_empty_state() else [init_csv_saved_data]

    notify_handler.attach_listener_command(dev_COMMAND_GET_RELAYS, lambda data: controller._background_loop.set(ControllerEvent(lambda: main_window.view.update_relays(conv_get_relays_data(data)))))
    notify_handler.attach_listener_command(dev_COMMAND_GET_CSV_ACTIVE, lambda data: controller._background_loop.set(ControllerEvent(lambda: main_window.view.set_running_csv(conv_get_csv_active_data(data)))))

    def get_last_or_new_csv_prog_then(after):
        if len(csv_saved_data) == 0 or csv_saved_data[-1].has_caught_csv():
            csv_saved_data.append(CsvProgConv())
        
        after(csv_saved_data[-1])

    notify_handler.attach_listener_command(dev_COMMAND_GET_CSV_PROG, lambda data: get_last_or_new_csv_prog_then(lambda csv_prog_conv: csv_prog_conv.catch_header(data)))
    notify_handler.attach_csv_notify_listener(lambda data: get_last_or_new_csv_prog_then(lambda csv_prog_conv: csv_prog_conv.catch_csv(data)))
    notify_handler.attach_listener_command(dev_COMMAND_GET_CSV_CUR_STAT, lambda data: csv_saved_data[-1].catch_update(data))

    def enable_relay():
        nums = main_window.view.get_selected_relay_numbers()
        if(len(nums) == 0):
            return
        
        peripheral.write_request(*uuid_pair_write, gen_command_alter_enable(nums))

    def disable_relay():
        nums = main_window.view.get_selected_relay_numbers()
        if(len(nums) == 0):
            return

        peripheral.write_request(*uuid_pair_write, gen_command_alter_disable(nums))

    def send_csv(select_args):
        perpetual = False
        num_iterations = 1
        
        if type(select_args) is CsvSelectIterationsRun:
            perpetual = False
            num_iterations = select_args.iterations

        if type(select_args) is CsvSelectRun:
            perpetual = True

        try:
            csv_bytes = gen_command_start_csv(select_args.file_path, perpetual, num_iterations)
            peripheral.write_request(*uuid_pair_write, csv_bytes[0:5])

            for cursor in range(5, len(csv_bytes), dev_command_csv_block_size):
                end_it = cursor + dev_command_csv_block_size
                peripheral.write_request(*uuid_pair_csv, csv_bytes[cursor:(end_it if end_it < len(csv_bytes) else len(csv_bytes))])
        except:
            import traceback
            traceback.print_exc()

            controller._launch_message("Error - Bad CSV format", main_window)

    def start_csv():
        csv_select_window = controller._launch_csv_select(main_window)
        csv_select_window.view.ev_submit.connect(send_csv)

    def stop_csv():
        peripheral.write_request(*uuid_pair_write, gen_command_csv_stop())

    def show_csv():
        select_window = controller._launch_select("Select the CSV:")
        for i, csv_prog_conv in enumerate(csv_saved_data):
            item = QListWidgetItem(f"{i+1}: CSV [Last Edited: {csv_prog_conv.get_last_edit().strftime("%Y-%m-%d %H:%M:%S")}]")
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setData(Qt.UserRole, csv_prog_conv)
            select_window.ui.list_widget.addItem(item)

        def on_select():
            if len(select_window.ui.list_widget.selectedItems()) != 1:
                return
            
            csv_prog_conv = select_window.ui.list_widget.selectedItems()[0].data(Qt.UserRole)
            controller._launch_csv_prog(main_window, csv_prog_conv)

            select_window.close()

        select_window.ui.select_button.clicked.connect(on_select)
    
    main_window.ui.enable_button.clicked.connect(enable_relay)
    main_window.ui.disable_button.clicked.connect(disable_relay)

    main_window.ui.start_csv_button.clicked.connect(start_csv)
    main_window.ui.stop_csv_button.clicked.connect(stop_csv)
    main_window.ui.show_csv_button.clicked.connect(show_csv)
