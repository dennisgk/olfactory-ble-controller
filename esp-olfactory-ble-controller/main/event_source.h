/* esp_event (event loop library) basic example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/

#ifndef EVENT_SOURCE_H_
#define EVENT_SOURCE_H_

#include "esp_event.h"
#include "esp_timer.h"
#include "blox.h"

typedef uint8_t relay_port_t;

#define NUM_RELAY_PORTS (relay_port_t)5

typedef uint8_t relay_msg_property_t;

#define COMMAND_GET_RELAYS (relay_msg_property_t)1
#define COMMAND_GET_CSV_ACTIVE (relay_msg_property_t)2
#define COMMAND_GET_CSV_PROG (relay_msg_property_t)3
#define COMMAND_GET_CSV_CUR_STAT (relay_msg_property_t)7

#define COMMAND_ALTER (relay_msg_property_t)4
#define COMMAND_CSV_START (relay_msg_property_t)5
#define COMMAND_CSV_STOP (relay_msg_property_t)6

#define RELAY_IGNORE (relay_msg_property_t)1
#define RELAY_ACTIVATE (relay_msg_property_t)2
#define RELAY_DEACTIVATE (relay_msg_property_t)3

#define CSV_INACTIVE (relay_msg_property_t)0
#define CSV_ACTIVE (relay_msg_property_t)1

#define CSV_TIME_NORMAL (relay_msg_property_t)1
#define CSV_TIME_RANDOM (relay_msg_property_t)2

#define CSV_RELAY_ON (relay_msg_property_t)1
#define CSV_RELAY_OFF (relay_msg_property_t)0
#define CSV_RELAY_RANDOM (relay_msg_property_t)2

#define CSV_RUN_NUMBER (relay_msg_property_t)2
#define CSV_RUN_PERPETUAL (relay_msg_property_t)3

#define COMMAND_CSV_BLOCK_SIZE (size_t)128

// format will be COMMAND_GET_CSV_PROG then SIZE then it_number then row_number then actual_time_millis (if app), port_states ONLY SENDING FINISHED

ESP_EVENT_DECLARE_BASE(RELAY_COMM_EVENT);

enum RelayCommEvent
{
    RELAY_ALTER_EVENT,
    RELAY_READ_CSV_EVENT
};

struct RelayCsvRowRelay
{
    relay_msg_property_t val_adj;
    uint32_t percentage;
};

struct RelayCsvRow
{
    blox tag;
    relay_msg_property_t time_adj;
    uint32_t time_val_1;
    uint32_t time_val_2;

    struct RelayCsvRowRelay relays[NUM_RELAY_PORTS];
};

struct RelayCsvIterationRowChoice
{
    relay_msg_property_t active;
    int64_t actual_time_millis;
    relay_msg_property_t port_states[NUM_RELAY_PORTS];
};

struct RelayCsvIterationChoice
{
    blox row_choices;
};

struct RelayCsvTable
{
    blox read_csv;

    uint32_t transfer_size;
    blox rows;
    relay_msg_property_t run_adj;
    uint32_t run_num;

    blox choices;
};

#endif