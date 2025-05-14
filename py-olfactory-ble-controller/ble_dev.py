import csv
import re
from datetime import datetime
from pydantic import BaseModel

dev_search_millis = 5000
dev_name = "OLFACTORY_BLE"
dev_num_relays = 5
dev_char_write = "bbbb"
dev_char_notify = "cccc"
dev_char_csv = "dddd"
dev_char_notify_csv = "eeee"
dev_command_csv_block_size = 128

dev_COMMAND_GET_RELAYS = 1
dev_COMMAND_GET_CSV_ACTIVE = 2
dev_COMMAND_GET_CSV_PROG = 3
dev_COMMAND_GET_CSV_CUR_STAT = 7

dev_COMMAND_ALTER = 4
dev_COMMAND_CSV_START = 5
dev_COMMAND_CSV_STOP = 6

dev_RELAY_IGNORE = 1
dev_RELAY_ACTIVATE = 2
dev_RELAY_DEACTIVATE = 3

dev_CSV_INACTIVE = 0
dev_CSV_ACTIVE = 1

dev_CSV_TIME_NORMAL = 1
dev_CSV_TIME_RANDOM = 2

dev_CSV_RELAY_ON = 1
dev_CSV_RELAY_OFF = 0
dev_CSV_RELAY_RANDOM = 2

dev_CSV_RUN_NUMBER = 2
dev_CSV_RUN_PERPETUAL = 3

def gen_command_get_relays_bytes():
    return bytes([dev_COMMAND_GET_RELAYS])

def gen_command_get_csv_active_bytes():
    return bytes([dev_COMMAND_GET_CSV_ACTIVE])

def gen_command_get_csv_cur_state_bytes():
    return bytes([dev_COMMAND_GET_CSV_CUR_STAT])

def gen_command_get_csv_prog_bytes():
    return bytes([dev_COMMAND_GET_CSV_PROG])

def conv_get_relays_data(data):
    return [True if data[1+x] == dev_RELAY_ACTIVATE else False for x in range(0, dev_num_relays)]

def conv_get_csv_active_data(data):
    return True if data[1] == dev_CSV_ACTIVE else False

def gen_command_alter_enable(nums):
    return bytes([dev_COMMAND_ALTER]) + bytes([dev_RELAY_ACTIVATE if x in nums else dev_RELAY_IGNORE for x in range(0, dev_num_relays)])

def gen_command_alter_disable(nums):
    return bytes([dev_COMMAND_ALTER]) + bytes([dev_RELAY_DEACTIVATE if x in nums else dev_RELAY_IGNORE for x in range(0, dev_num_relays)])

def gen_command_csv_stop():
    return bytes([dev_COMMAND_CSV_STOP])

tag_header = "TAG"
time_header = "TIME"
relay_header = "R"

time_random_tag = "RANDOM"
relay_random_tag = "RANDOM"
relay_on_tag = "ON"
relay_off_tag = "OFF"

def parse_csv_time_ms(time_str):
    time_val_re = re.findall(r"(\d*\.?\d*)(MS|S)", time_str)[0]
    time_val = float(time_val_re[0])

    if time_val_re[1] == "MS":
        pass
    elif time_val_re[1] == "S":
        time_val = time_val * 1000
    else:
        raise ValueError("Error - Bad csv time")
    
    return int(round(time_val))

def combine_added_bytes(added):
    return bytes(len(added).to_bytes(4, "little")) + added

def gen_command_start_csv(file_path, perpetual, num_runs):
    all_out_bytes = bytes([])

    if perpetual:
        all_out_bytes = all_out_bytes + bytes([dev_CSV_RUN_PERPETUAL])
    else:
        all_out_bytes = all_out_bytes + bytes([dev_CSV_RUN_NUMBER]) + num_runs.to_bytes(4, "little")

    num_rows = 0

    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        if reader.fieldnames != ["TAG", "TIME"] + [f"{relay_header}{x}" for x in range(1, dev_num_relays + 1)]:
            raise ValueError("Error - Invalid headers")
        
        for row in reader:
            num_rows = num_rows + 1

            tag_ascii = row["TAG"].encode("ascii")
            all_out_bytes = all_out_bytes + combine_added_bytes(tag_ascii)

            time_words = re.split(r"\s+", row["TIME"])
            if time_words[0] == time_random_tag:
                time_val_1 = parse_csv_time_ms(time_words[1])
                time_val_2 = parse_csv_time_ms(time_words[2])

                if time_val_1 > time_val_2:
                    temp = time_val_1
                    time_val_1 = time_val_2
                    time_val_2 = temp

                if time_val_1 == time_val_2:
                    time_val_2 = time_val_2 + 1

                time_bytes = bytes([dev_CSV_TIME_RANDOM]) + time_val_1.to_bytes(4, "little") + time_val_2.to_bytes(4, "little");
            else:
                time_val = parse_csv_time_ms(time_words[0])
                time_bytes = bytes([dev_CSV_TIME_NORMAL]) + time_val.to_bytes(4, "little")
            
            all_out_bytes = all_out_bytes + time_bytes

            for x in range(1, dev_num_relays + 1):
                relay_words = re.split(r"\s+", row[f"{relay_header}{x}"])

                if relay_words[0] == relay_random_tag:
                    relay_val = int(round(float(re.findall(r"(\d*\.?\d*)%", relay_words[1])[0]) * 1000))
                    relay_bytes = bytes([dev_CSV_RELAY_RANDOM]) + relay_val.to_bytes(4, "little")
                elif relay_words[0] == relay_on_tag:
                    relay_bytes = bytes([dev_CSV_RELAY_ON])
                elif relay_words[0] == relay_off_tag:
                    relay_bytes = bytes([dev_CSV_RELAY_OFF])

                all_out_bytes = all_out_bytes + relay_bytes

    if num_rows == 0:
        raise ValueError("Error - No rows")

    return bytes([dev_COMMAND_CSV_START]) + combine_added_bytes(all_out_bytes)

class CsvConvSchemaRowRelay(BaseModel):
    pass

class CsvConvSchemaRandomRowRelay(CsvConvSchemaRowRelay):
    percentage: float

class CsvConvSchemaSetRowRelay(CsvConvSchemaRowRelay):
    val: bool

class CsvConvSchemaRowTime(BaseModel):
    pass

class CsvConvSchemaRandomRowTime(CsvConvSchemaRowTime):
    time_val_1: int
    time_val_2: int

class CsvConvSchemaSetRowTime(CsvConvSchemaRowTime):
    time_val: int

class CsvConvSchemaRow(BaseModel):
    tag: str
    time: CsvConvSchemaRowTime
    relays: list[CsvConvSchemaRowRelay]

class CsvConvSchema:
    def __init__(self, caught_csv):
        self.csv_rows = []

        x = 0

        if caught_csv[0] == dev_CSV_RUN_PERPETUAL:
            self._perpetual = True
            x = x + 1

        if caught_csv[0] == dev_CSV_RUN_NUMBER:
            self._perpetual = False
            self._run_num = int.from_bytes(caught_csv[1:5], "little")
            x = x + 5

        while x < len(caught_csv):
            tag_len = int.from_bytes(caught_csv[x:x+4], "little")
            x = x + 4
            tag = caught_csv[x:x+tag_len].decode("ascii")
            x = x + tag_len

            time = None

            time_byte = caught_csv[x]
            x = x + 1

            if time_byte == dev_CSV_TIME_RANDOM:
                time_val_1 = int.from_bytes(caught_csv[x:x+4], "little")
                x = x + 4
                time_val_2 = int.from_bytes(caught_csv[x:x+4], "little")
                x = x + 4

                time = CsvConvSchemaRandomRowTime(time_val_1=time_val_1, time_val_2=time_val_2)
            
            if time_byte == dev_CSV_TIME_NORMAL:
                time_val = int.from_bytes(caught_csv[x:x+4], "little")
                x = x + 4

                time = CsvConvSchemaSetRowTime(time_val=time_val)

            relays = []

            for _relay_num in range(0, dev_num_relays):
                relay_byte = caught_csv[x]
                x = x + 1

                if relay_byte == dev_CSV_RELAY_RANDOM:
                    relay_perc_int = int.from_bytes(caught_csv[x:x+4], "little")
                    relay_perc = float(relay_perc_int / 1000)
                    x = x + 4

                    relays.append(CsvConvSchemaRandomRowRelay(percentage=relay_perc))

                if relay_byte == dev_CSV_RELAY_ON:
                    relays.append(CsvConvSchemaSetRowRelay(val=True))

                if relay_byte == dev_CSV_RELAY_OFF:
                    relays.append(CsvConvSchemaSetRowRelay(val=False))
            
            self.csv_rows.append(CsvConvSchemaRow(tag=tag, time=time, relays=relays))

class CsvProgConv():
    def __init__(self):
        self._last_edit = datetime.now()
        self._is_empty_state = True

        self._must_catch_csv = 0
        self._must_catch_fillin = 0
        self._caught_csv = bytes([])
        self._caught_fillin = bytes([])
        self._caught_multi = bytes([])

        self._csv_schema = None
        self._csv_fillin = dict()
        self._csv_fillin_millis = dict()

        self._saved_iteration_row_data = []
        self._ev_iteration_handler = []
        self._ev_row_handler = []

    def _emit_ev_row(self, it, row):
        self._saved_iteration_row_data.append((it, row))

        for h in self._ev_row_handler:
            h(it, row)

    def _emit_iteration(self, num):
        for h in self._ev_iteration_handler:
            h(num)

    def add_handlers(self, ev_iteration_handler, ev_row_handler):
        self._ev_iteration_handler.append(ev_iteration_handler)
        self._ev_row_handler.append(ev_row_handler)

    def remove_handlers(self, ev_iteration_handler, ev_row_handler):
        self._ev_iteration_handler.remove(ev_iteration_handler)
        self._ev_row_handler.remove(ev_row_handler)

    def get_saved_iteration_row_data(self):
        return self._saved_iteration_row_data

    def is_empty_state(self):
        return self._is_empty_state

    def has_caught_csv(self):
        return (not self.is_empty_state()) and (len(self._caught_multi) >= self._must_catch_csv + self._must_catch_fillin)

    def get_row_count(self):
        return len(self._csv_schema.csv_rows)

    def catch_header(self, data):
        self._last_edit = datetime.now()
        if len(data) == 1:
            return
        
        self._must_catch_csv = int.from_bytes(data[1:5], "little")
        self._must_catch_fillin = int.from_bytes(data[5:9], "little")
        
        self._is_empty_state = False
        self._form_csv_schema_if_needed()

    def catch_csv(self, data):
        self._last_edit = datetime.now()

        self._caught_multi = self._caught_multi + data
        self._form_csv_schema_if_needed()

    def _form_csv_schema_if_needed(self):
        if self._csv_schema == None and self.has_caught_csv():

            catch_offset = 0

            if len(self._caught_csv) < self._must_catch_csv:
                max_catch = min(self._must_catch_csv - len(self._caught_csv), len(self._caught_multi))

                self._caught_csv = self._caught_csv + self._caught_multi[catch_offset:(catch_offset + max_catch)]
                catch_offset = catch_offset + max_catch

            if len(self._caught_fillin) < self._must_catch_fillin:
                max_catch = min(self._must_catch_fillin - len(self._caught_fillin), len(self._caught_multi) - catch_offset)

                self._caught_fillin = self._caught_fillin + self._caught_multi[catch_offset:(catch_offset + max_catch)]

            self._csv_schema = CsvConvSchema(self._caught_csv)

            last_it = None
            last_row = None
            last_millis = None

            x = 0
            while x < len(self._caught_fillin):
                i = int.from_bytes(self._caught_fillin[x:x+4], "little")
                x = x + 4
                j = int.from_bytes(self._caught_fillin[x:x+4], "little")
                x = x + 4

                time = int.from_bytes(self._caught_fillin[x:x+8], "little")
                x = x + 8

                relays = [True if self._caught_fillin[x+y] == dev_RELAY_ACTIVATE else False for y in range(0, dev_num_relays)]
                x = x + dev_num_relays

                self._catch_update_deob(i, j, relays, last_it, last_row, last_millis)

                last_it = i
                last_row = j
                last_millis = time

            self._catch_update_deob(None, None, None, last_it, last_row, last_millis)

    def get_last_edit(self):
        return self._last_edit
    
    def get_headers(self):
        return [tag_header, f"EXPECTED {time_header} (MS)", f"ACTUAL {time_header} (MS)"] + [f"{relay_header}{x+1}" for x in range(0, dev_num_relays)] + ["R CONFIG"]
    
    def get_row(self, it, row):

        time_text = ""
        if type(self._csv_schema.csv_rows[row].time) is CsvConvSchemaSetRowTime:
            time_text = f"{self._csv_schema.csv_rows[row].time.time_val}MS"
        
        if type(self._csv_schema.csv_rows[row].time) is CsvConvSchemaRandomRowTime:
            time_text = f"RANDOM {self._csv_schema.csv_rows[row].time.time_val_1}MS {self._csv_schema.csv_rows[row].time.time_val_2}MS"

        act_time = ""
        if it in self._csv_fillin_millis and row in self._csv_fillin_millis.get(it).keys():
            act_time = f"{self._csv_fillin_millis.get(it).get(row)}MS"
        
        relay_arr = []
        relay_changes = []

        for x in range(0, dev_num_relays):
            if type(self._csv_schema.csv_rows[row].relays[x]) is CsvConvSchemaRandomRowRelay:
                relay_arr.append(f"RANDOM {self._csv_schema.csv_rows[row].relays[x].percentage:.3f}%")
                relay_changes.append(f"R{x+1}={"ON" if self._csv_fillin.get(it).get(row)[x] else "OFF"}")

            if type(self._csv_schema.csv_rows[row].relays[x]) is CsvConvSchemaSetRowRelay:
                relay_arr.append("ON" if self._csv_schema.csv_rows[row].relays[x].val else "OFF")

        return [self._csv_schema.csv_rows[row].tag, time_text, act_time] + relay_arr + [",".join(relay_changes)]

    def _catch_update_deob(self, current_it, current_row, current_ports, last_it, last_row, last_millis):

        if current_it != None and current_row != None and current_ports != None:
            if current_it not in self._csv_fillin.keys():
                if current_it not in self._csv_fillin_millis.keys():
                    self._emit_iteration(current_it)
                self._csv_fillin.update(dict([(current_it, dict())]))
            self._csv_fillin.get(current_it).update(dict([(current_row, current_ports)]))
            self._emit_ev_row(current_it, current_row)

        if last_it != None and last_row != None and last_millis != None:
            if last_it not in self._csv_fillin_millis.keys():
                if last_it not in self._csv_fillin.keys():
                    self._emit_iteration(last_it)
                self._csv_fillin_millis.update(dict([(last_it, dict())]))
            self._csv_fillin_millis.get(last_it).update(dict([(last_row, last_millis)]))
            self._emit_ev_row(last_it, last_row)

    def catch_update(self, data):
        self._last_edit = datetime.now()
        if len(data) == 1:
            return
        
        if len(data) == 1 + 4 + 4 + dev_num_relays:
            self._catch_update_deob(
                int.from_bytes(data[1:5], "little"),
                int.from_bytes(data[5:9], "little"),
                [True if data[9+y] == dev_RELAY_ACTIVATE else False for y in range(0, dev_num_relays)],
                None,
                None,
                None
            )
        
        if len(data) == 1 + 4 + 4 + dev_num_relays + 4 + 4 + 8:
            self._catch_update_deob(
                int.from_bytes(data[1:5], "little"),
                int.from_bytes(data[5:9], "little"),
                [True if data[9+y] == dev_RELAY_ACTIVATE else False for y in range(0, dev_num_relays)],
                int.from_bytes(data[(9+dev_num_relays):(13+dev_num_relays)], "little"),
                int.from_bytes(data[(13+dev_num_relays):(17+dev_num_relays)], "little"),
                int.from_bytes(data[(17+dev_num_relays):(25+dev_num_relays)], "little"),
            )
        
        if len(data) == 1 + 4 + 4 + 8:
            self._catch_update_deob(
                None,
                None,
                None,
                int.from_bytes(data[1:5], "little"),
                int.from_bytes(data[5:9], "little"),
                int.from_bytes(data[9:17], "little"),
            )

