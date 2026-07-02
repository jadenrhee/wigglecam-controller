#pragma once
#include <stdint.h>
#include "hardware/i2c.h"

typedef uint8_t (*i2c_read_fn)(uint8_t reg);
typedef void (*i2c_write_fn)(uint8_t reg, uint8_t value);

void i2c_slave_setup(i2c_inst_t *i2c, uint sda, uint scl, uint8_t addr,
                     i2c_read_fn read_fn, i2c_write_fn write_fn);
