#pragma once
#include <stdint.h>
#include "hardware/i2c.h"

void ina219_init(i2c_inst_t *i2c, uint8_t address);
int ina219_bus_mv(void);       // battery voltage in mV, -1 if absent
int ina219_current_ma(void);   // battery current in mA (signed)
