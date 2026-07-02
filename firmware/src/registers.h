// I2C register map — the contract with the Pi. Keep in sync with
// docs/protocol.md.
#pragma once
#include <stdint.h>

enum {
    REG_WHO_AM_I     = 0x00,  // R  : always 0xCA
    REG_STATUS       = 0x01,  // R  : bit0 flash_busy, bit1 event_pending
    REG_TRIGGER      = 0x02,  // W  : 1 = sync pulse; 2 = flash + sync
    REG_FLASH_MS     = 0x03,  // RW : flash duration, clamped 1..150
    REG_FLASH_PCT    = 0x04,  // RW : flash current 0..100 %
    REG_FIRE_FLASH   = 0x05,  // W  : flash pulse only (no sync)
    REG_VBAT_L       = 0x06,  // R  : battery mV, little-endian u16
    REG_VBAT_H       = 0x07,
    REG_IBAT_L       = 0x08,  // R  : battery mA, little-endian i16
    REG_IBAT_H       = 0x09,
    REG_ENC_DELTA    = 0x0A,  // R  : signed detent count, clears on read
    REG_BUTTONS      = 0x0B,  // R  : bit0 shutter, bit1 enc push; clears
    REG_LED_R        = 0x0C,  // RW
    REG_LED_G        = 0x0D,  // RW
    REG_LED_B        = 0x0E,  // RW
    REG_LED_APPLY    = 0x0F,  // W  : latch RGB to the WS2812
    REG_COUNT        = 0x10,
};

#define WHO_AM_I_VALUE 0xCA
#define STATUS_FLASH_BUSY  (1u << 0)
#define STATUS_EVENT       (1u << 1)
