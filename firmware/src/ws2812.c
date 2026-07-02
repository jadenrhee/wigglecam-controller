// WS2812B status LED via PIO.

#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"

#include "ws2812.pio.h"
#include "ws2812.h"

static PIO pio;
static uint sm;

void ws2812_init(uint pin) {
    pio = pio0;
    uint offset = pio_add_program(pio, &ws2812_program);
    sm = pio_claim_unused_sm(pio, true);

    pio_gpio_init(pio, pin);
    pio_sm_set_consecutive_pindirs(pio, sm, pin, 1, true);
    pio_sm_config c = ws2812_program_get_default_config(offset);
    sm_config_set_sideset_pins(&c, pin);
    sm_config_set_out_shift(&c, false, true, 24);   // MSB first, autopull
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
    float div = clock_get_hz(clk_sys) / 8000000.0f; // 8 MHz SM clock
    sm_config_set_clkdiv(&c, div);
    pio_sm_init(pio, sm, offset, &c);
    pio_sm_set_enabled(pio, sm, true);

    ws2812_set(0, 8, 0);   // dim green: alive
}

void ws2812_set(uint8_t r, uint8_t g, uint8_t b) {
    uint32_t grb = ((uint32_t)g << 16) | ((uint32_t)r << 8) | b;
    pio_sm_put_blocking(pio, sm, grb << 8);
}
