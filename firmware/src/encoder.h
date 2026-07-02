#pragma once
#include "pico/stdlib.h"

void encoder_init(uint pin_a, uint pin_b);
void encoder_irq(uint gpio);
int8_t encoder_take_delta(void);
