cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(camctrl C CXX ASM)
set(CMAKE_C_STANDARD 11)

pico_sdk_init()

add_executable(camctrl
    src/main.c
    src/i2c_slave.c
    src/ina219.c
    src/encoder.c
    src/flash_led.c
    src/ws2812.c
)

pico_generate_pio_header(camctrl ${CMAKE_CURRENT_LIST_DIR}/src/ws2812.pio)

target_include_directories(camctrl PRIVATE src)

# Board carries a W25Q128JVSIQ (16 MB); the stock boot2 for Winbond
# W25Q-series applies. Override the Pico default 2 MB size.
target_compile_definitions(camctrl PRIVATE
    PICO_FLASH_SIZE_BYTES=16777216
)

target_link_libraries(camctrl
    pico_stdlib
    hardware_i2c
    hardware_pwm
    hardware_pio
    hardware_irq
)

pico_add_extra_outputs(camctrl)
