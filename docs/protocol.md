# Pi ⇄ Camera Controller protocol

Bus: I2C, RP2040 as slave at **0x17** on the Pi's I2C1 (GPIO2/3,
400 kHz; the Pi 5's onboard 1.8 kΩ pullups serve the bus). Register
semantics follow SMBus conventions: write `[reg]` then data bytes
(auto-increment), or write `[reg]` + repeated-start read.

A second signal, **ATTN** (RP2040 GPIO7 → Pi GPIO18), goes high while
any button/encoder event is latched — the Pi can poll cheaply or take
a GPIO interrupt instead of polling I2C.

The capture-sync line (**RP2040 GPIO6 → Pi GPIO17**) pulses high when
a trigger fires; the Pi's capture loop waits on this edge so the
exposure lands inside the flash window.

## Register map

| Addr | Name | R/W | Meaning |
|------|------|-----|---------|
| 0x00 | WHO_AM_I | R | always 0xCA |
| 0x01 | STATUS | R | bit0 flash busy, bit1 event pending |
| 0x02 | TRIGGER | W | 1 = sync pulse only; 2 = flash + sync (flash reaches steady current ~5 ms before the sync edge) |
| 0x03 | FLASH_MS | RW | flash duration, clamped 1–150 ms (default 30) |
| 0x04 | FLASH_PCT | RW | flash current 0–100 % of 1.00 A/branch (default 80) |
| 0x05 | FIRE_FLASH | W | flash pulse without sync (e.g. focus assist) |
| 0x06–07 | VBAT | R | battery voltage, mV, little-endian u16 |
| 0x08–09 | IBAT | R | battery current, mA, little-endian i16 |
| 0x0A | ENC_DELTA | R | signed detent count since last read (clears) |
| 0x0B | BUTTONS | R | bit0 shutter, bit1 encoder push (clears; drops ATTN) |
| 0x0C–0E | LED R/G/B | RW | status LED color staging |
| 0x0F | LED_APPLY | W | latch staged RGB to the WS2812B |

## Safety behavior (firmware-enforced, mirrors the hardware)

- Flash pulse hard-capped at 150 ms; 800 ms cooldown between pulses
  (SOT-23 sink transient thermal budget).
- The PWM pin idles low and the board's 100 kΩ pulldown holds the
  current-sink reference at 0 V through reset/boot — the flash cannot
  fire until firmware explicitly commands it.
- 500 ms hardware watchdog; a hung firmware resets to flash-off.

## Example (Pi side, python3-smbus2)

```python
from smbus2 import SMBus
bus = SMBus(1)
assert bus.read_byte_data(0x17, 0x00) == 0xCA
bus.write_byte_data(0x17, 0x03, 40)   # 40 ms flash
bus.write_byte_data(0x17, 0x04, 90)   # 90 % current
bus.write_byte_data(0x17, 0x02, 2)    # flash + sync capture
mv = bus.read_word_data(0x17, 0x06)   # battery mV
```
