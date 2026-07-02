// INA219 driver, fixed configuration for this board:
// 10 mΩ shunt, PGA ±320 mV, 12-bit, current_LSB = 100 µA
// → CAL = 0.04096 / (100e-6 * 0.01) = 40960  (INA219 datasheet §8.5.1)

#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "ina219.h"

#define REG_CONFIG   0x00
#define REG_BUS_V    0x02
#define REG_CURRENT  0x04
#define REG_CAL      0x05

static i2c_inst_t *bus;
static uint8_t addr;
static bool present;

static bool wr16(uint8_t reg, uint16_t val) {
    uint8_t b[3] = {reg, (uint8_t)(val >> 8), (uint8_t)val};
    return i2c_write_timeout_us(bus, addr, b, 3, false, 2000) == 3;
}

static bool rd16(uint8_t reg, uint16_t *out) {
    uint8_t b[2];
    if (i2c_write_timeout_us(bus, addr, &reg, 1, true, 2000) != 1)
        return false;
    if (i2c_read_timeout_us(bus, addr, b, 2, false, 2000) != 2)
        return false;
    *out = ((uint16_t)b[0] << 8) | b[1];
    return true;
}

void ina219_init(i2c_inst_t *i2c, uint8_t address) {
    bus = i2c;
    addr = address;
    // 32V range bit irrelevant (1S battery), PGA /8 (±320 mV),
    // 12-bit bus + shunt, continuous both: 0x399F (datasheet default
    // with PGA kept at /8).
    present = wr16(REG_CONFIG, 0x399F) && wr16(REG_CAL, 40960);
}

int ina219_bus_mv(void) {
    uint16_t v;
    if (!present || !rd16(REG_BUS_V, &v))
        return -1;
    return (v >> 3) * 4;          // LSB = 4 mV
}

int ina219_current_ma(void) {
    uint16_t v;
    if (!present || !rd16(REG_CURRENT, &v))
        return 0;
    return (int16_t)v / 10;       // LSB = 100 µA → /10 = mA
}
