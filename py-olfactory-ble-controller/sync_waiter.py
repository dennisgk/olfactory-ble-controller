import threading
from datetime import datetime

class SyncWaiter():
    def __init__(self):
        self._start_time = datetime.now()

        self._quit_event = threading.Event()

        self._var = []
        self._var_mutex = threading.Lock()
        self._var_event = threading.Event()

        self._downtime_var = []
        self._downtime_var_mutex = threading.Lock()
        self._downtime_var_event = threading.Event()

        self._downtime_thread = threading.Thread(target = self._downtime_waiter)
        self._downtime_thread.start()

    def has_quit(self):
        return self._quit_event.is_set()
        
    def wait_var(self):
        if(self.has_quit()):
            return None

        self._var_mutex.acquire()
        if(len(self._var) > 0):
            ret_val = self._var[0]
            self._var.pop(0)
            self._var_mutex.release()
            return ret_val
        
        self._var_mutex.release()

        self._var_event.wait()
        if(self.has_quit()):
            return None
        
        self._var_mutex.acquire()
        ret_val = self._var[0]
        self._var.pop(0)
        self._var_mutex.release()
        
        return ret_val

    def remove_where(self, where_callback):
        self._downtime_var_mutex.acquire()
        self._var_mutex.acquire()

        rem_var_list = []
        rem_downtime_var_list = []

        for x in range(0, len(self._var)):
            if(where_callback(self._var[x])):
                rem_var_list.append(self._var[x])

        for x in range(0, len(self._downtime_var)):
            if(where_callback(self._downtime_var[x][1])):
                rem_downtime_var_list.append(self._downtime_var[x])

        for x in rem_var_list:
            self._var.remove(x)

        for x in rem_downtime_var_list:
            self._downtime_var.remove(x)

        self._var_mutex.release()
        self._downtime_var_mutex.release()

    def set(self, v):
        if(self.has_quit()):
            return

        self._var_mutex.acquire()
        self._var.append(v)
        self._var_mutex.release()
        self._var_event.set()
        self._var_event.clear()

    def set_downtime(self, v, millis):
        if(self.has_quit()):
            return
        
        self._downtime_var_mutex.acquire()

        val_insert = (self._elapsed_millis() + millis, v)
        was_inserted = False
        for x in range(0, len(self._downtime_var)):
            if(val_insert[0] < self._downtime_var[x][0]):
                self._downtime_var.insert(x, val_insert)
                was_inserted = True
                break

        if(not was_inserted):
            self._downtime_var.append(val_insert)
        
        self._downtime_var_mutex.release()
        self._downtime_var_event.set()
        self._downtime_var_event.clear()

    def _elapsed_millis(self):
        dt = datetime.now() - self._start_time
        ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
        return ms

    def quit(self):
        self._quit_event.set()

        self._var_event.set()
        self._var_event.clear()
        self._downtime_var_event.set()
        self._downtime_var_event.clear()

    def len_var_queue(self):
        return len(self._var)

    def len_downtime_var_queue(self):
        return len(self._downtime_var)

    def _downtime_next_millis(self):
        self._downtime_var_mutex.acquire()

        timeout_millis = None
        if(len(self._downtime_var) > 0):
            timeout_millis = self._downtime_var[0][0] - self._elapsed_millis()
        
        self._downtime_var_mutex.release()

        return timeout_millis

    def _downtime_waiter(self):

        while True:
            if(self.has_quit()):
                break

            timeout_millis = self._downtime_next_millis()

            while(timeout_millis == None):
                self._downtime_var_event.wait()
                if(self.has_quit()):
                    break

                timeout_millis = self._downtime_next_millis()
            
            if(timeout_millis != None and timeout_millis > 0):
                self._downtime_var_event.wait(timeout_millis * 0.001)
                if(self.has_quit()):
                    break

            self._downtime_var_mutex.acquire()

            del_ordered_index = len(self._downtime_var)

            for x in range(0, len(self._downtime_var)):
                if(self._elapsed_millis() >= self._downtime_var[x][0]):
                    self.set(self._downtime_var[x][1])
                else:
                    del_ordered_index = x
                    break

            for x in range(0, del_ordered_index):
                self._downtime_var.pop(0)

            self._downtime_var_mutex.release()