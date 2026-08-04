// Flash current control with hardware-mirroring safety limits.
//
// PIN_FLASH_PWM feeds an RC filter + divider producing the op-amp
// current-sink reference (100 % duty = 0.5 V = 1.00 A per branch).
// Firmware enforces total LED-on time <= FLASH_MAX_MS (the ~5 ms
// pre-sync settle counts against the budget), cooldown >=
// FLASH_COOLDOWN_MS (thermal duty for the SOT-23 sinks), and a pin
// that idles LOW so the board's 100k pulldown and this driver agree
// the flash is off.
//
// Everything here is nonblocking: callers start a sequence, and
// flash_poll() (main loop) walks it through its states. Nothing
// sleeps, so nothing here may stall the I2C slave IRQ.

#include "pico/stdlib.h"
#include "hardware/pwm.h"

#include "board.h"
#include "flash_led.h"

#define SETTLE_MS      5   // LED-on to sync edge, inside FLASH_MAX_MS
#define SYNC_PULSE_MS 10   // sync pulse width when no flash is involved

enum {
    F_IDLE,
    F_SETTLE,   // LEDs on, waiting for steady current before sync
    F_FIRING,   // LEDs on (sync already raised if requested)
    F_SYNC,     // sync-only pulse, LEDs off
};

static uint slice, chan;
static volatile uint8_t state = F_IDLE;
static absolute_time_t t_step;        // SETTLE->FIRING / SYNC->IDLE
static absolute_time_t pulse_end;     // LED off (measured from LED on)
static absolute_time_t cooldown_end;

void flash_init(void) {
    gpio_init(PIN_CAM_SYNC);
    gpio_set_dir(PIN_CAM_SYNC, GPIO_OUT);
    gpio_put(PIN_CAM_SYNC, 0);

    gpio_set_function(PIN_FLASH_PWM, GPIO_FUNC_PWM);
    slice = pwm_gpio_to_slice_num(PIN_FLASH_PWM);
    chan = pwm_gpio_to_channel(PIN_FLASH_PWM);
    // 125 MHz / (62.5 * 100) = 20 kHz, far above the 160 Hz RC pole,
    // so the reference is clean DC.
    pwm_set_clkdiv(slice, 62.5f);
    pwm_set_wrap(slice, 99);
    pwm_set_chan_level(slice, chan, 0);
    pwm_set_enabled(slice, true);
}

bool flash_busy(void) {
    return state != F_IDLE;   // any pulse or sync in progress owns the line
}

static void set_level(uint8_t pct) {
    pwm_set_chan_level(slice, chan, pct > 100 ? 100 : pct);
}

bool flash_fire(uint8_t ms, uint8_t pct, bool with_sync) {
    if (state != F_IDLE ||
        absolute_time_diff_us(get_absolute_time(), cooldown_end) > 0)
        return false;                 // active or cooling down: refuse
    if (ms == 0 || pct == 0)
        return false;
    if (ms > FLASH_MAX_MS)
        ms = FLASH_MAX_MS;

    absolute_time_t start = get_absolute_time();
    set_level(pct);
    // pulse_end runs from LED-on, so settle + lit time <= FLASH_MAX_MS
    pulse_end = delayed_by_ms(start, ms);
    if (with_sync && ms > SETTLE_MS) {
        // give the LEDs ~5 ms to reach steady current; flash_poll()
        // then raises the sync line and the Pi captures on that rising
        // edge while the scene stays lit for the rest of the pulse.
        t_step = delayed_by_ms(start, SETTLE_MS);
        state = F_SETTLE;
    } else {
        if (with_sync)
            gpio_put(PIN_CAM_SYNC, 1);   // pulse too short to settle
        state = F_FIRING;
    }
    return true;
}

void flash_sync_pulse_only(void) {
    if (state != F_IDLE)
        return;                       // a flash sequence owns the line
    gpio_put(PIN_CAM_SYNC, 1);
    t_step = make_timeout_time_ms(SYNC_PULSE_MS);
    state = F_SYNC;
}

void flash_poll(void) {
    absolute_time_t now = get_absolute_time();
    switch (state) {
    case F_SETTLE:
        if (absolute_time_diff_us(now, t_step) <= 0) {
            gpio_put(PIN_CAM_SYNC, 1);
            state = F_FIRING;
        }
        break;
    case F_FIRING:
        if (absolute_time_diff_us(now, pulse_end) <= 0) {
            set_level(0);
            gpio_put(PIN_CAM_SYNC, 0);
            cooldown_end = make_timeout_time_ms(FLASH_COOLDOWN_MS);
            state = F_IDLE;
        }
        break;
    case F_SYNC:
        if (absolute_time_diff_us(now, t_step) <= 0) {
            gpio_put(PIN_CAM_SYNC, 0);
            state = F_IDLE;
        }
        break;
    default:
        break;
    }
}
