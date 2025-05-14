#ifndef __BLE_HANDLER_H__
#define __BLE_HANDLER_H__

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "esp_nimble_hci.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

#define APP_TAG "OLFACTORY_BLE"

static uint16_t cur_conn_handle;

void olfactory_ble_init(const struct ble_gatt_svc_def gatt_svcs[]);

#endif