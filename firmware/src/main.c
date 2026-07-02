// WiggleCam Camera Controller firmware.
//
// Role: real-time/analog sidecar for the Raspberry Pi 5. The Pi is
// I2C master (we are a 16-register slave at 0x17); this core handles
// flash current control with hard safety limits, shutter debounce,
// EC11 quadrature, battery telemetry via INA219, the WS2812 status
// LED, and the camera-sync pulse.

#include "pico/stdlib.h"
#include "hardware/watchdog.h"
#include "hardware/i2c.h"

#include "board.h"
#include "registers.h"
#include "i2c_slave.h"
#include "ina219.h"
#include "encoder.h"
#include "flash_led.h"
#include "ws2812.h"

static uint8_t regs[REG_COUNT];

// ---------------------------------------------------------------- events --
static volatile uint8_t button_events;
static volatile uint32_t shutter_last_ms;

static void update_attn(void) {
    gpio_put(PIN_ATTN, button_events != 0);
}

static void shutter_irq(uint gpio, uint32_t events) {
    (void)events;
    uint32_t now = to_ms_since_boot(get_absolute_time());
    if (gpio == PIN_SHUTTER) {
        if (now - shutter_last_ms > 30) {   // debounce (RC did stage 1)
            button_events |= 1u << 0;
            shutter_last_ms = now;
        }
    } else if (gpio == PIN_ENC_SW) {
        button_events |= 1u << 1;
    } else {
        encoder_irq(gpio);
    }
    update_attn();
}

// ------------------------------------------------------------- I2C hooks --
// Called from the slave IRQ: master reads register `addr`.
static uint8_t on_read(uint8_t addr) {
    switch (addr) {
    case REG_WHO_AM_I:  return WHO_AM_I_VALUE;
    case REG_STATUS:
        return (flash_busy() ? STATUS_FLASH_BUSY : 0) |
               (button_events ? STATUS_EVENT : 0);
    case REG_ENC_DELTA: {
        int8_t d = encoder_take_delta();
        return (uint8_t)d;
    }
    case REG_BUTTONS: {
        uint8_t b = button_events;
        button_events = 0;
        update_attn();
        return b;
    }
    default:
        return addr < REG_COUNT ? regs[addr] : 0xFF;
    }
}

static void on_write(uint8_t addr, uint8_t value) {
    switch (addr) {
    case REG_TRIGGER:
        if (value == 2 && regs[REG_FLASH_PCT] > 0)
            flash_fire(regs[REG_FLASH_MS], regs[REG_FLASH_PCT], true);
        else
            flash_sync_pulse_only();
        break;
    case REG_FIRE_FLASH:
        flash_fire(regs[REG_FLASH_MS], regs[REG_FLASH_PCT], false);
        break;
    case REG_FLASH_MS:
        regs[addr] = value > FLASH_MAX_MS ? FLASH_MAX_MS
                     : (value == 0 ? 1 : value);
        break;
    case REG_FLASH_PCT:
        regs[addr] = value > 100 ? 100 : value;
        break;
    case REG_LED_APPLY:
        ws2812_set(regs[REG_LED_R], regs[REG_LED_G], regs[REG_LED_B]);
        break;
    default:
        if (addr < REG_COUNT)
            regs[addr] = value;
    }
}

int main(void) {
    // status/attention outputs first: defined levels ASAP after boot
    gpio_init(PIN_ATTN);
    gpio_set_dir(PIN_ATTN, GPIO_OUT);
    gpio_put(PIN_ATTN, 0);
    gpio_init(PIN_DEBUG_LED);
    gpio_set_dir(PIN_DEBUG_LED, GPIO_OUT);

    flash_init();          // claims PIN_FLASH_PWM, holds reference at 0
    ws2812_init(PIN_WS2812);
    encoder_init(PIN_ENC_A, PIN_ENC_B);

    // inputs
    for (uint pin = 0; pin < 2; pin++) {
        uint p = pin == 0 ? PIN_SHUTTER : PIN_ENC_SW;
        gpio_init(p);
        gpio_set_dir(p, GPIO_IN);
        gpio_pull_up(p);   // belt-and-braces; board has 10k pullups
        gpio_set_irq_enabled(p, GPIO_IRQ_EDGE_FALL, true);
    }
    gpio_set_irq_enabled(PIN_ENC_A, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL,
                         true);
    gpio_set_irq_enabled(PIN_ENC_B, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL,
                         true);
    gpio_set_irq_callback(&shutter_irq);
    irq_set_enabled(IO_IRQ_BANK0, true);

    // internal I2C master -> INA219
    i2c_init(i2c0, 400 * 1000);
    gpio_set_function(PIN_I2C_INT_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C_INT_SCL, GPIO_FUNC_I2C);
    ina219_init(i2c0, INA219_ADDR);

    // Pi-facing I2C slave
    regs[REG_FLASH_MS] = 30;
    regs[REG_FLASH_PCT] = 80;
    i2c_slave_setup(i2c1, PIN_I2C_SLAVE_SDA, PIN_I2C_SLAVE_SCL,
                    I2C_SLAVE_ADDR, on_read, on_write);

    watchdog_enable(500, true);

    uint32_t last_batt = 0, last_blink = 0;
    while (true) {
        watchdog_update();
        flash_poll();      // enforces pulse end + cooldown
        uint32_t now = to_ms_since_boot(get_absolute_time());
        if (now - last_batt >= 250) {
            last_batt = now;
            int mv = ina219_bus_mv();
            int ma = ina219_current_ma();
            regs[REG_VBAT_L] = mv & 0xFF;
            regs[REG_VBAT_H] = (mv >> 8) & 0xFF;
            regs[REG_IBAT_L] = ma & 0xFF;
            regs[REG_IBAT_H] = (ma >> 8) & 0xFF;
        }
        if (now - last_blink >= 500) {
            last_blink = now;
            gpio_xor_mask(1u << PIN_DEBUG_LED);   // heartbeat
        }
        tight_loop_contents();
    }
}
