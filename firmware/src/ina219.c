// INA219 driver, fixed configuration for this board:
// PGA ±320 mV, 12-bit, current_LSB = 200 µA
// → CAL = trunc(0.04096 / (200e-6 · R_shunt))  (INA219 datasheet §8.5.1)
// 200 µA puts full scale at 32767 · 200 µA = ±6.55 A, covering the
// design's 5 A worst case; 100 µA would clip the signed current
// register at 3.28 A and wrap negative above it.
//
// Effective shunt resistance: the part (R19) is 10 mΩ, but the layout's
// sense taps are not Kelvin — they join the 1.5 mm battery trace a few
// mm from the shunt pads, putting roughly 3 mΩ of copper inside the
// sense loop, so uncorrected current/power read ~30 % high. Trim
// SHUNT_EFF_MOHM against a series bench meter at bring-up (expect
// something near 13).
#define SHUNT_EFF_MOHM 10
// CAL = 0.04096 / (200e-6 · R), R in mΩ → 204800 / mΩ (trunc)
#define INA219_CAL (204800 / SHUNT_EFF_MOHM)

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
    present = wr16(REG_CONFIG, 0x399F) && wr16(REG_CAL, INA219_CAL);
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
    return (int16_t)v / 5;        // LSB = 200 µA → /5 = mA
}
