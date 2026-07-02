// Register-file I2C slave on the RP2040's hardware I2C, IRQ-driven.
// Protocol: write [reg] then bytes (auto-increment), or write [reg]
// then repeated-start read (auto-increment). Matches SMBus-style
// access from the Pi (i2cget/i2cset/smbus2).

#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "hardware/irq.h"

#include "i2c_slave.h"

static i2c_inst_t *inst;
static i2c_read_fn rd;
static i2c_write_fn wr;
static uint8_t reg_addr;
static bool addr_received;

static void slave_irq(void) {
    i2c_hw_t *hw = i2c_get_hw(inst);
    uint32_t status = hw->intr_stat;

    if (status & I2C_IC_INTR_STAT_R_START_DET_BITS) {
        hw->clr_start_det;
        addr_received = false;   // new transaction: first byte = reg
    }
    if (status & I2C_IC_INTR_STAT_R_RX_FULL_BITS) {
        while (hw->rxflr) {
            uint8_t b = (uint8_t)hw->data_cmd;
            if (!addr_received) {
                reg_addr = b;
                addr_received = true;
            } else {
                wr(reg_addr++, b);
            }
        }
    }
    if (status & I2C_IC_INTR_STAT_R_RD_REQ_BITS) {
        hw->clr_rd_req;
        hw->data_cmd = rd(reg_addr++);
    }
    if (status & I2C_IC_INTR_STAT_R_TX_ABRT_BITS)
        (void)hw->clr_tx_abrt;
    if (status & I2C_IC_INTR_STAT_R_STOP_DET_BITS)
        (void)hw->clr_stop_det;
}

void i2c_slave_setup(i2c_inst_t *i2c, uint sda, uint scl, uint8_t addr,
                     i2c_read_fn read_fn, i2c_write_fn write_fn) {
    inst = i2c;
    rd = read_fn;
    wr = write_fn;

    gpio_set_function(sda, GPIO_FUNC_I2C);
    gpio_set_function(scl, GPIO_FUNC_I2C);
    // no gpio pullups here: the Pi's onboard 1.8k resistors own the bus

    i2c_init(i2c, 400 * 1000);
    i2c_set_slave_mode(i2c, true, addr);

    i2c_hw_t *hw = i2c_get_hw(i2c);
    hw->intr_mask = I2C_IC_INTR_MASK_M_RX_FULL_BITS |
                    I2C_IC_INTR_MASK_M_RD_REQ_BITS |
                    I2C_IC_INTR_MASK_M_START_DET_BITS |
                    I2C_IC_INTR_MASK_M_STOP_DET_BITS |
                    I2C_IC_INTR_MASK_M_TX_ABRT_BITS;

    uint irqn = i2c == i2c0 ? I2C0_IRQ : I2C1_IRQ;
    irq_set_exclusive_handler(irqn, slave_irq);
    irq_set_enabled(irqn, true);
}
