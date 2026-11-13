#ifndef NETWORK_MONITOR_H
#define NETWORK_MONITOR_H
#include "xil_io.h"
#include "xil_printf.h"
#include <stdint.h>
#ifndef NETWORK_ENABLE
#define NETWORK_ENABLE 0U
#endif
static void network_log(int force) {
    static uint32_t last=0xffffffffU;
    static uint32_t last_in=0xffffffffU, last_skip=0xffffffffU;
    uint32_t s=Xil_In32(0xA0020000U);
    uint32_t done=s>>16;
    uint32_t image_in=Xil_In32(0xA0030000U), image_skip=Xil_In32(0xA0030008U);
    if(force || s!=last || image_in!=last_in || image_skip!=last_skip || (s&0x30U)) {
        last=s;last_in=image_in;last_skip=image_skip;
        xil_printf("NET: enabled=%u busy=%u done=%u image_in=%u image_skip=%u infer_ms=%u fault=%u status=%08X.\r\n",
            (s>>3)&1U,(s>>1)&1U,done,image_in,image_skip,
            Xil_In32(0xA0020008U)/250000U,(s>>4)&3U,s);
    }
}
#endif
