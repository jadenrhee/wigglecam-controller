// Pin map — must match hardware/skidl/circuit.py exactly.
#pragma once

#define PIN_UART_TX      0   // -> Pi RXD (GPIO15)
#define PIN_UART_RX      1   // <- Pi TXD (GPIO14)
#define PIN_I2C_SLAVE_SDA 2  // Pi I2C1 (Pi GPIO2)
#define PIN_I2C_SLAVE_SCL 3  // Pi I2C1 (Pi GPIO3)
#define PIN_I2C_INT_SDA  4   // internal bus: INA219
#define PIN_I2C_INT_SCL  5
#define PIN_CAM_SYNC     6   // -> Pi GPIO17, capture-sync pulse
#define PIN_ATTN         7   // -> Pi GPIO18, "event pending" flag
#define PIN_SHUTTER      10  // active low, RC-conditioned
#define PIN_ENC_A        11
#define PIN_ENC_B        12
#define PIN_ENC_SW       13  // active low
#define PIN_FLASH_PWM    16  // filtered PWM -> current-sink reference
#define PIN_WS2812       22
#define PIN_DEBUG_LED    25

#define I2C_SLAVE_ADDR   0x17
#define INA219_ADDR      0x40

// Flash safety limits (mirror the hardware: 100k pulldown keeps the
// reference at 0 V until firmware drives it)
#define FLASH_MAX_MS     150
#define FLASH_COOLDOWN_MS 800
