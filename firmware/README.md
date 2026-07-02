# Camera Controller firmware

RP2040 firmware (Pico SDK, C). See [../docs/protocol.md](../docs/protocol.md)
for the I2C register map the Pi talks to.

## Build

```bash
export PICO_SDK_PATH=~/pico-sdk
# any arm-none-eabi toolchain with newlib; xpack works well:
export PICO_TOOLCHAIN_PATH=~/tools/xpack-arm-none-eabi-gcc-14.2.1-1.1/bin
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
make -C build -j4
```

Flash: hold BOOTSEL while plugging USB-C, then copy
`build/camctrl.uf2` to the RPI-RP2 drive.
