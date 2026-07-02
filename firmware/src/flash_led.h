#pragma once
#include <stdbool.h>
#include <stdint.h>

void flash_init(void);
void flash_fire(uint8_t ms, uint8_t pct, bool with_sync);
void flash_sync_pulse_only(void);
void flash_poll(void);
bool flash_busy(void);
