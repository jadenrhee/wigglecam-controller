// EC11 quadrature decode, IRQ-driven with a full state-transition
// table (rejects invalid transitions = contact bounce immunity).
// EC11E18244AU: 18 detents/36 pulses — 2 valid transitions per detent
// in each direction with this table; divide accordingly.

#include "pico/stdlib.h"
#include "encoder.h"
#include "board.h"

static volatile int32_t count;
static volatile uint8_t prev_state;

// index: (prev<<2)|curr; value: -1, 0, +1
static const int8_t TRANSITION[16] = {
     0, -1, +1,  0,
    +1,  0,  0, -1,
    -1,  0,  0, +1,
     0, +1, -1,  0,
};

void encoder_init(uint pin_a, uint pin_b) {
    gpio_init(pin_a); gpio_set_dir(pin_a, GPIO_IN); gpio_pull_up(pin_a);
    gpio_init(pin_b); gpio_set_dir(pin_b, GPIO_IN); gpio_pull_up(pin_b);
    prev_state = (gpio_get(PIN_ENC_A) << 1) | gpio_get(PIN_ENC_B);
}

void encoder_irq(uint gpio) {
    (void)gpio;
    uint8_t curr = (gpio_get(PIN_ENC_A) << 1) | gpio_get(PIN_ENC_B);
    count += TRANSITION[(prev_state << 2) | curr];
    prev_state = curr;
}

int8_t encoder_take_delta(void) {
    int32_t c = count;
    count = 0;
    int32_t detents = c / 2;      // 2 valid edges per detent
    if (detents > 127) detents = 127;
    if (detents < -128) detents = -128;
    return (int8_t)detents;
}
