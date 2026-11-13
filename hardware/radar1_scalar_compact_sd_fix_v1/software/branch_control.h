#ifndef RADAR_BRANCH_CONTROL_H
#define RADAR_BRANCH_CONTROL_H
#include <stdint.h>
#include "xil_io.h"
#include "xil_printf.h"
#include "network_monitor.h"

/* GPIO channel 1: four sticky input fault bits. Channel 2: output-only.
 * bit0 imaging, bit1 storage, bit2 one-bit imaging. Set before radar input;
 * the quantizer locks this mode with its first accepted sample. */
#define BRANCH_CONTROL_ADDR 0xA0010008U
static inline int enable_capture_mode(uint32_t branches, uint32_t onebit) {
    uint32_t command;
    if ((branches & ~3U) || onebit > 1U || (onebit && !(branches & 1U))) {
        xil_printf("FAIL: invalid branch/image mode request.\r\n");
        return -1;
    }
    if ((NETWORK_ENABLE && !onebit) || ((Xil_In32(0xA0020000U)>>8)&255U)!=0x71U) {
        xil_printf("FAIL: network BIT signature/mode mismatch.\r\n");return -1;
    }
    command = branches | (onebit << 2) | (NETWORK_ENABLE << 3);
    Xil_Out32(BRANCH_CONTROL_ADDR, command);
    if ((Xil_In32(BRANCH_CONTROL_ADDR) & 15U) != command) {
        xil_printf("FAIL: branch/mode control readback; use one-bit BIT.\r\n");
        return -1;
    }
    xil_printf("BRANCH_ENABLE=%u (bit0=imaging, bit1=storage).\r\n", branches);
    xil_printf("IMAGE_MODE_REQUEST=%s, amplitude=64, I/Q signed separately.\r\n",
               onebit ? "ONE_BIT" : "RAW");
    xil_printf("NETWORK_REQUEST=%u, scalar-compact-exp-v1, power64 gain-squared, PL inference.\r\n", NETWORK_ENABLE);
    network_log(1);
    return 0;
}
#endif
