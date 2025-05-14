#define APP_TAG "OLFACTORY_BLE"
#include <stdio.h>
#include "ble_handler.h"
#include "event_source.h"
#include "blox.h"
#include "driver/gpio.h"
#include "esp_random.h"

// THERE IS A STACK OVERFLOW ERROR IN csv_task_runner
// THE DATA FOR THE BLUETOOTH STUFF NEEDS TO BE SENT IN PACKETS TO NOT EXCEED 256 or 128 bytes MAYBE CREATE ANOTHER CHAR WHICH RECEIVES AFTER INIT SEND

esp_event_loop_handle_t ev_loop;

ESP_EVENT_DEFINE_BASE(RELAY_COMM_EVENT);

uint16_t notify_handle;
uint16_t notify_handle_csv;

relay_msg_property_t relay_state[NUM_RELAY_PORTS];
gpio_num_t relay_port_nums[NUM_RELAY_PORTS] = {GPIO_NUM_32, GPIO_NUM_33, GPIO_NUM_25, GPIO_NUM_26, GPIO_NUM_27};

struct RelayCsvTable csv_table = {0};
TaskHandle_t csv_task_spawn_handle = NULL;

static int device_notify(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    return 0;
}

static int device_notify_csv(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    return 0;
}

static int device_csv(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (csv_table.read_csv.length < csv_table.transfer_size)
    {
        blox_append_array(uint8_t, csv_table.read_csv, ctxt->om->om_data, ctxt->om->om_len);

        if (csv_table.read_csv.length >= csv_table.transfer_size)
        {
            esp_event_post_to(ev_loop, RELAY_COMM_EVENT, RELAY_READ_CSV_EVENT, csv_table.read_csv.data, csv_table.transfer_size, portMAX_DELAY);
        }
    }

    return 0;
}

static void resp_notify(uint16_t conn_handle, relay_msg_property_t prop, uint8_t *data, size_t size)
{
    const char *out_start_buf = "";
    struct os_mbuf *resp_buf = ble_hs_mbuf_from_flat(out_start_buf, 0);
    os_mbuf_append(resp_buf, &prop, sizeof(relay_msg_property_t));
    os_mbuf_append(resp_buf, data, size);
    ble_gatts_notify_custom(conn_handle, notify_handle, resp_buf);
}

static void resp_csv_prog_notify(uint16_t conn_handle)
{
    if (csv_task_spawn_handle == NULL)
    {
        resp_notify(conn_handle, COMMAND_GET_CSV_PROG, NULL, 0);
        return;
    }

    relay_msg_property_t prop = COMMAND_GET_CSV_PROG;

    const char *out_start_buf = "";
    struct os_mbuf *resp_buf = ble_hs_mbuf_from_flat(out_start_buf, 0);
    os_mbuf_append(resp_buf, &prop, sizeof(relay_msg_property_t));

    blox full_resp_data = blox_create(uint8_t);

    for (size_t i = 0; i < csv_table.choices.length; i++)
    {
        for (size_t j = 0; j < blox_get(struct RelayCsvIterationChoice, csv_table.choices, i).row_choices.length; j++)
        {
            struct RelayCsvIterationRowChoice choice = blox_get(struct RelayCsvIterationRowChoice, blox_get(struct RelayCsvIterationChoice, csv_table.choices, i).row_choices, j);

            if (choice.active == CSV_ACTIVE)
            {
                continue;
            }

            blox_append_array(uint8_t, full_resp_data, &i, sizeof(uint32_t));
            blox_append_array(uint8_t, full_resp_data, &j, sizeof(uint32_t));

            blox_append_array(uint8_t, full_resp_data, &choice.actual_time_millis, sizeof(int64_t));
            blox_append_array(uint8_t, full_resp_data, choice.port_states, sizeof(relay_msg_property_t) * NUM_RELAY_PORTS);
        }
    }

    os_mbuf_append(resp_buf, &csv_table.read_csv.length, sizeof(uint32_t));
    os_mbuf_append(resp_buf, &full_resp_data.length, sizeof(uint32_t));
    ble_gatts_notify_custom(conn_handle, notify_handle, resp_buf);

    for (uint32_t cursor = 0; cursor < csv_table.read_csv.length; cursor += COMMAND_CSV_BLOCK_SIZE)
    {
        uint32_t val_size = COMMAND_CSV_BLOCK_SIZE < csv_table.read_csv.length - cursor ? COMMAND_CSV_BLOCK_SIZE : csv_table.read_csv.length - cursor;

        resp_buf = ble_hs_mbuf_from_flat(out_start_buf, 0);
        os_mbuf_append(resp_buf, ((uint8_t *)csv_table.read_csv.data) + cursor, val_size * sizeof(uint8_t));
        ble_gatts_notify_custom(conn_handle, notify_handle_csv, resp_buf);
    }

    for (uint32_t cursor = 0; cursor < full_resp_data.length; cursor += COMMAND_CSV_BLOCK_SIZE)
    {
        uint32_t val_size = COMMAND_CSV_BLOCK_SIZE < full_resp_data.length - cursor ? COMMAND_CSV_BLOCK_SIZE : full_resp_data.length - cursor;

        resp_buf = ble_hs_mbuf_from_flat(out_start_buf, 0);
        os_mbuf_append(resp_buf, ((uint8_t *)full_resp_data.data) + cursor, val_size * sizeof(uint8_t));
        ble_gatts_notify_custom(conn_handle, notify_handle_csv, resp_buf);
    }

    blox_free(full_resp_data);
}

static void resp_csv_prog_single_notify(uint16_t conn_handle, relay_msg_property_t is_last_active)
{
    if (csv_task_spawn_handle == NULL)
    {
        resp_notify(conn_handle, COMMAND_GET_CSV_CUR_STAT, NULL, 0);
        return;
    }

    uint32_t last_it = 0;
    uint32_t last_row = 0;

    uint32_t now_it = csv_table.choices.length - 1;
    uint32_t now_row = blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices.length - 1;

    if (now_row > 0)
    {
        // then were good
        last_it = now_it;
        last_row = now_row - 1;
    }
    else if (now_row == 0 && now_it == 0)
    {
        // were starting at the beginning, no last
        last_it = now_it;
        last_row = now_row;
    }
    else
    {
        // we need to loop back one
        last_it = now_it - 1;
        last_row = blox_get(struct RelayCsvIterationChoice, csv_table.choices, csv_table.choices.length - 2).row_choices.length - 1;
    }

    blox full_resp_data = blox_create(uint8_t);
    blox_append_array(uint8_t, full_resp_data, &now_it, sizeof(uint32_t));
    blox_append_array(uint8_t, full_resp_data, &now_row, sizeof(uint32_t));

    struct RelayCsvIterationRowChoice choice = blox_get(struct RelayCsvIterationRowChoice, blox_get(struct RelayCsvIterationChoice, csv_table.choices, now_it).row_choices, now_row);

    if (is_last_active == CSV_INACTIVE)
    {
        blox_append_array(uint8_t, full_resp_data, choice.port_states, sizeof(relay_msg_property_t) * NUM_RELAY_PORTS);
    }
    else
    {
        blox_append_array(uint8_t, full_resp_data, &choice.actual_time_millis, sizeof(int64_t));
    }

    if (is_last_active == CSV_INACTIVE && (last_it != now_it || last_row != now_row))
    {
        choice = blox_get(struct RelayCsvIterationRowChoice, blox_get(struct RelayCsvIterationChoice, csv_table.choices, last_it).row_choices, last_row);
        blox_append_array(uint8_t, full_resp_data, &last_it, sizeof(uint32_t));
        blox_append_array(uint8_t, full_resp_data, &last_row, sizeof(uint32_t));

        blox_append_array(uint8_t, full_resp_data, &choice.actual_time_millis, sizeof(int64_t));
    }

    resp_notify(conn_handle, COMMAND_GET_CSV_CUR_STAT, full_resp_data.data, full_resp_data.length);

    blox_free(full_resp_data);
}

// Write data to ESP32 defined as server
static int device_write(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (ctxt->om->om_len == 0)
    {
        return 0;
    }

    switch (ctxt->om->om_data[0])
    {
    case COMMAND_GET_RELAYS:
    {
        resp_notify(conn_handle, COMMAND_GET_RELAYS, relay_state, sizeof(relay_msg_property_t) * NUM_RELAY_PORTS);
        break;
    }
    case COMMAND_GET_CSV_ACTIVE:
    {
        relay_msg_property_t act = csv_task_spawn_handle == NULL ? CSV_INACTIVE : CSV_ACTIVE;

        resp_notify(conn_handle, COMMAND_GET_CSV_ACTIVE, &act, sizeof(uint8_t));
        break;
    }
    case COMMAND_GET_CSV_PROG:
    {
        resp_csv_prog_notify(conn_handle);
        break;
    }
    case COMMAND_GET_CSV_CUR_STAT:
    {
        resp_csv_prog_single_notify(conn_handle, CSV_INACTIVE);
        break;
    }
    case COMMAND_ALTER:
    {
        if (ctxt->om->om_len != sizeof(relay_msg_property_t) + (sizeof(relay_msg_property_t) * NUM_RELAY_PORTS))
        {
            break;
        }

        esp_event_post_to(ev_loop, RELAY_COMM_EVENT, RELAY_ALTER_EVENT, ctxt->om->om_data + sizeof(relay_msg_property_t), sizeof(relay_msg_property_t) * NUM_RELAY_PORTS, portMAX_DELAY);
        break;
    }
    case COMMAND_CSV_START:
    {
        if (csv_task_spawn_handle != NULL)
        {
            break;
        }

        if (ctxt->om->om_len != sizeof(relay_msg_property_t) + sizeof(uint32_t))
        {
            break;
        }

        uint32_t size = *((uint32_t *)(ctxt->om->om_data + sizeof(relay_msg_property_t)));
        if (size == 0)
        {
            break;
        }

        csv_table.transfer_size = size;
        csv_table.read_csv = blox_create(uint8_t);

        break;
    }
    case COMMAND_CSV_STOP:
    {
        if (csv_task_spawn_handle == NULL)
        {
            break;
        }

        xTaskNotifyGive(csv_task_spawn_handle);
        break;
    }
    default:
        break;
    }

    return 0;
}

/*
command line example

help
on NUMBER...NUMBER ->
off NUMBER...NUMBER
csvproc WITH THE TOPS AS IDENTIFIER,TIME,NUMBER,NUMBER,NUMBER,NUMBER,NUMBER WHERE NUMBER HAS ON/OFF STATES
debugproc save/verbose/nothing

convert all these things to binary

*/

// Array of pointers to other service definitions
// UUID - Universal Unique Identifier
static const struct ble_gatt_svc_def gatt_svcs[] = {
    {.type = BLE_GATT_SVC_TYPE_PRIMARY,
     .uuid = BLE_UUID16_DECLARE(0x189), // Define UUID for device type
     .characteristics = (struct ble_gatt_chr_def[]){
         {.uuid = BLE_UUID16_DECLARE(0xBBBB), // Define UUID for writing
          .flags = BLE_GATT_CHR_F_WRITE,
          .access_cb = device_write},
         {.uuid = BLE_UUID16_DECLARE(0xCCCC), // Define UUID for notifying
          .flags = BLE_GATT_CHR_F_NOTIFY,
          .val_handle = &notify_handle,
          .access_cb = device_notify},
         {.uuid = BLE_UUID16_DECLARE(0xEEEE), // define UUID for notifying csv stuff
          .flags = BLE_GATT_CHR_F_NOTIFY,
          .val_handle = &notify_handle_csv,
          .access_cb = device_notify_csv},
         {.uuid = BLE_UUID16_DECLARE(0xDDDD), // Define UUID for csv transfer
          .flags = BLE_GATT_CHR_F_WRITE,
          .access_cb = device_csv},
         {0}}},
    {0}};

static void relay_alter_handler(void *handler_args, esp_event_base_t base, int32_t id, void *event_data)
{
    relay_msg_property_t *relay_new_state = (relay_msg_property_t *)event_data;
    for (relay_port_t i = 0; i < NUM_RELAY_PORTS; i++)
    {
        if ((relay_new_state[i] == RELAY_IGNORE) || (relay_state[i] == relay_new_state[i]))
            continue;

        if (relay_new_state[i] == RELAY_ACTIVATE)
        {
            gpio_set_level(relay_port_nums[i], 1);
            relay_state[i] = RELAY_ACTIVATE;
        }

        if (relay_new_state[i] == RELAY_DEACTIVATE)
        {
            gpio_set_level(relay_port_nums[i], 0);
            relay_state[i] = RELAY_DEACTIVATE;
        }
    }

    resp_notify(cur_conn_handle, COMMAND_GET_RELAYS, relay_state, sizeof(relay_msg_property_t) * NUM_RELAY_PORTS);
}

void csv_task_runner(void *pv)
{
    uint32_t num_runs_taken = 0;

    relay_msg_property_t is_running = CSV_ACTIVE;
    resp_notify(cur_conn_handle, COMMAND_GET_CSV_ACTIVE, &is_running, sizeof(relay_msg_property_t));

    csv_table.choices = blox_create(struct RelayCsvIterationChoice);

    resp_csv_prog_notify(cur_conn_handle);

    while (is_running == CSV_ACTIVE)
    {
        blox_stuff(struct RelayCsvIterationChoice, csv_table.choices);
        blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices = blox_create(struct RelayCsvIterationRowChoice);

        for (size_t i = 0; i < csv_table.rows.length; i++)
        {
            blox_stuff(struct RelayCsvIterationRowChoice, blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices);

#define LATEST_ROW blox_back(struct RelayCsvIterationRowChoice, blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices)

            LATEST_ROW.active = CSV_ACTIVE;
            LATEST_ROW.actual_time_millis =
                esp_timer_get_time() / (int64_t)1000;

            struct RelayCsvRow row = blox_get(struct RelayCsvRow, csv_table.rows, i);

            for (relay_port_t z = 0; z < NUM_RELAY_PORTS; z++)
            {
                if (row.relays[z].val_adj == CSV_RELAY_ON)
                {
                    ESP_LOGI(APP_TAG, "sending on to relay %d", z + 1);
                    LATEST_ROW.port_states[z] = RELAY_ACTIVATE;
                    // send on
                }
                if (row.relays[z].val_adj == CSV_RELAY_OFF)
                {
                    ESP_LOGI(APP_TAG, "sending off to relay %d", z + 1);
                    LATEST_ROW.port_states[z] = RELAY_DEACTIVATE;
                    // send off
                }
                if (row.relays[z].val_adj == CSV_RELAY_RANDOM)
                {
                    ESP_LOGI(APP_TAG, "random sent to relay %d", z + 1);
                    uint32_t range_random = 100000 + 1;
                    uint32_t rand_val = (((uint32_t)esp_random()) & range_random);

                    if (rand_val <= row.relays[z].percentage)
                    {
                        LATEST_ROW.port_states[z] = RELAY_ACTIVATE;
                    }
                    else
                    {
                        LATEST_ROW.port_states[z] = RELAY_DEACTIVATE;
                    }

                    // do random REMEMBER THE PERCENTAGE IS REALLY 1000 * 100%
                    // mjust call xTaskNotifyGive(xTaskHandle);
                }
            }

            resp_csv_prog_single_notify(cur_conn_handle, CSV_INACTIVE);
            esp_event_post_to(ev_loop, RELAY_COMM_EVENT, RELAY_ALTER_EVENT, LATEST_ROW.port_states, sizeof(relay_msg_property_t) * NUM_RELAY_PORTS, portMAX_DELAY);

#undef LATEST_ROW

            uint32_t ticks_to_wait = row.time_val_1;

            if (row.time_adj == CSV_TIME_RANDOM)
            {
                uint32_t range = row.time_val_2 - row.time_val_1 + 1;
                ticks_to_wait = (((uint32_t)esp_random()) % range) + row.time_val_1;
            }

            uint32_t notified = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(ticks_to_wait));

            blox_back(struct RelayCsvIterationRowChoice, blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices).active = CSV_INACTIVE;
            blox_back(struct RelayCsvIterationRowChoice, blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices).actual_time_millis =
                (esp_timer_get_time() / (int64_t)1000) -
                blox_back(struct RelayCsvIterationRowChoice, blox_back(struct RelayCsvIterationChoice, csv_table.choices).row_choices).actual_time_millis;

            if (notified > 0)
            {
                is_running = CSV_INACTIVE;
                break;
            }
        }

        num_runs_taken++;

        if (csv_table.run_adj == CSV_RUN_NUMBER && num_runs_taken >= csv_table.run_num)
        {
            is_running = CSV_INACTIVE;
            break;
        }
    }

    resp_csv_prog_single_notify(cur_conn_handle, CSV_ACTIVE);

    for (size_t i = 0; i < csv_table.rows.length; i++)
    {
        blox_free(blox_get(struct RelayCsvRow, csv_table.rows, i).tag);
    }

    for (size_t i = 0; i < csv_table.choices.length; i++)
    {
        blox_free(blox_get(struct RelayCsvIterationChoice, csv_table.choices, i).row_choices);
    }

    blox_free(csv_table.rows);
    blox_free(csv_table.read_csv);
    blox_free(csv_table.choices);

    csv_task_spawn_handle = NULL;

    resp_notify(cur_conn_handle, COMMAND_GET_CSV_ACTIVE, &is_running, sizeof(relay_msg_property_t));

    vTaskDelete(NULL);
}

static void relay_read_csv_handler(void *handler_args, esp_event_base_t base, int32_t id, void *event_data)
{
    csv_table.rows = blox_create(struct RelayCsvRow);

    uint32_t cursor = 0;

    csv_table.run_adj = *((relay_msg_property_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
    cursor += sizeof(relay_msg_property_t);

    if (csv_table.run_adj == CSV_RUN_NUMBER)
    {
        csv_table.run_num = *((uint32_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
        cursor += sizeof(uint32_t);
    }

    while (cursor < csv_table.transfer_size)
    {
        struct RelayCsvRow row = {0};

        uint32_t tag_size = *((uint32_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
        cursor += sizeof(uint32_t);

        ESP_LOGI(APP_TAG, "tag_size: %d", (int)tag_size);

        row.tag = blox_create(char);
        blox_append_array(char, row.tag, (char *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)), tag_size);
        cursor += tag_size;

        row.time_adj = *((relay_msg_property_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
        cursor += sizeof(relay_msg_property_t);

        if (row.time_adj == CSV_TIME_NORMAL)
        {
            row.time_val_1 = *((uint32_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
            cursor += sizeof(uint32_t);
        }
        if (row.time_adj == CSV_TIME_RANDOM)
        {
            row.time_val_1 = *((uint32_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
            cursor += sizeof(uint32_t);
            row.time_val_2 = *((uint32_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
            cursor += sizeof(uint32_t);
        }

        for (relay_port_t i = 0; i < NUM_RELAY_PORTS; i++)
        {
            row.relays[i].val_adj = *((relay_msg_property_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
            cursor += sizeof(relay_msg_property_t);

            if (row.relays[i].val_adj == CSV_RELAY_RANDOM)
            {
                row.relays[i].percentage = *((uint32_t *)((uint8_t *)event_data + (sizeof(uint8_t) * cursor)));
                cursor += sizeof(uint32_t);
            }
        }

        blox_push(struct RelayCsvRow, csv_table.rows, row);
    }

    xTaskCreate(csv_task_runner, "CSV_TASK_RUNNER", /*4096*/ 9216, NULL, tskIDLE_PRIORITY + 5, &csv_task_spawn_handle);
}

// this must start a task with a bunch of delays - xTaskNotifyWait, xTaskNotify
// have the regular event loop
// 2 diff events -> 1 push -- pushes the event to the stack -> 1 run -- runs the event on the other loop -> and this is always using xTaskNotifyWait for next run or on push

void app_main()
{
    nvs_flash_init(); // 1 - Initialize NVS flash using

    for (relay_port_t i = 0; i < NUM_RELAY_PORTS; i++)
    {
        relay_state[i] = RELAY_DEACTIVATE;
        gpio_set_direction(relay_port_nums[i], GPIO_MODE_OUTPUT);
        gpio_set_level(relay_port_nums[i], 0);
    }

    esp_event_loop_args_t loop_args = {
        .queue_size = 10,
        .task_name = "loop_task",
        .task_priority = uxTaskPriorityGet(NULL),
        .task_stack_size = 9216,
        .task_core_id = tskNO_AFFINITY};

    ESP_ERROR_CHECK(esp_event_loop_create(&loop_args, &ev_loop));

    ESP_ERROR_CHECK(esp_event_handler_instance_register_with(ev_loop, RELAY_COMM_EVENT, RELAY_ALTER_EVENT, relay_alter_handler, ev_loop, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register_with(ev_loop, RELAY_COMM_EVENT, RELAY_READ_CSV_EVENT, relay_read_csv_handler, ev_loop, NULL));

    olfactory_ble_init(gatt_svcs);
}
