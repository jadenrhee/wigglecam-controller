// Flash current control with hardware-mirroring safety limits.
//
// PIN_FLASH_PWM feeds an RC filter + divider producing the op-amp
// current-sink reference (100 % duty = 0.5 V = 1.00 A per branch).
// Firmware enforces: pulse <= FLASH_MAX_MS, cooldown >= FLASH_COOLDOWN_MS
// (thermal duty for the SOT-23 sinks), and the pin idles LOW so the
// board's 100k pulldown and this driver agree the flash is off.

#include "pico/stdlib.h"
#include "hardware/pwm.h"

#include "board.h"
#include "flash_led.h"

static uint slice, chan;
static absolute_time_t pulse_end = {0};
static absolute_time_t cooldown_end = {0};
static volatile bool busy;

void flash_init(void) {
    gpio_init(PIN_CAM_SYNC);
    gpio_set_dir(PIN_CAM_SYNC, GPIO_OUT);
    gpio_put(PIN_CAM_SYNC, 0);

    gpio_set_function(PIN_FLASH_PWM, GPIO_FUNC_PWM);
    slice = pwm_gpio_to_slice_num(PIN_FLASH_PWM);
    chan = pwm_gpio_to_channel(PIN_FLASH_PWM);
    // 125 MHz / (62.5 * 100) = 20 kHz — far above the 160 Hz RC pole,
    // so the reference is clean DC.
    pwm_set_clkdiv(slice, 62.5f);
    pwm_set_wrap(slice, 99);
    pwm_set_chan_level(slice, chan, 0);
    pwm_set_enabled(slice, true);
}

bool flash_busy(void) { return busy; }

static void set_level(uint8_t pct) {
    pwm_set_chan_level(slice, chan, pct > 100 ? 100 : pct);
}

void flash_fire(uint8_t ms, uint8_t pct, bool with_sync) {
    if (busy || absolute_time_diff_us(get_absolute_time(),
                                      cooldown_end) > 0)
        return;                       // still cooling down: refuse
    if (ms == 0 || pct == 0)
        return;
    if (ms > FLASH_MAX_MS)
        ms = FLASH_MAX_MS;

    busy = true;
    set_level(pct);
    if (with_sync) {
        // give the LEDs ~5 ms to reach steady current, then raise the
        // sync line; the Pi captures on this rising edge while the
        // scene is lit for the remainder of the pulse.
        sleep_ms(5);
        gpio_put(PIN_CAM_SYNC, 1);
    }
    pulse_end = make_timeout_time_ms(ms);
}

void flash_sync_pulse_only(void) {
    gpio_put(PIN_CAM_SYNC, 1);
    sleep_ms(10);
    gpio_put(PIN_CAM_SYNC, 0);
}

void flash_poll(void) {
    if (busy && absolute_time_diff_us(get_absolute_time(),
                                      pulse_end) <= 0) {
        set_level(0);
        gpio_put(PIN_CAM_SYNC, 0);
        cooldown_end = make_timeout_time_ms(FLASH_COOLDOWN_MS);
        busy = false;
    }
}
