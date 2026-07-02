#pragma once
#include <stdint.h>
#include "pico/stdlib.h"

void ws2812_init(uint pin);
void ws2812_set(uint8_t r, uint8_t g, uint8_t b);
