#include <stdint.h>
#include <stddef.h>
#include "xil_printf.h"

#define TABLE_BYTES 11377128U
extern const unsigned char _binary_aq_ar_bin_start[TABLE_BYTES];
extern const unsigned char _binary_aq_ar_bin_end[];
/* These are the original imaging allocations, not the DMA capture pool. */
#define TABLE_ADDR ((uintptr_t)0x23000000U)
#define DISPLAY_A  ((uintptr_t)0x25000000U)
#define DISPLAY_B  ((uintptr_t)0x26000000U)

int initialize_imaging_buffers(void) {
    size_t i;
    const uint64_t *source=(const uint64_t *)_binary_aq_ar_bin_start;
    volatile uint64_t *table=(volatile uint64_t *)TABLE_ADDR;
    volatile uint64_t *a=(volatile uint64_t *)DISPLAY_A;
    volatile uint64_t *b=(volatile uint64_t *)DISPLAY_B;
    if ((uintptr_t)_binary_aq_ar_bin_end-(uintptr_t)_binary_aq_ar_bin_start!=TABLE_BYTES)
        return -1;
    /* Called with D-cache disabled, before DMA is armed or radar triggered. */
    for (i=0;i<TABLE_BYTES/sizeof(uint64_t);++i) {
        table[i]=source[i];
        a[i]=UINT64_MAX;
        b[i]=UINT64_MAX;
    }
    for (i=0;i<TABLE_BYTES/sizeof(uint64_t);++i)
        if (table[i]!=source[i] || a[i]!=UINT64_MAX || b[i]!=UINT64_MAX) return -1;
    xil_printf("IMAGING_INIT_PASS: AQ_AR=0x23000000, displays=0x25000000/0x26000000, bytes=%u.\r\n",TABLE_BYTES);
    xil_printf("Image preprocessing: startup mode selected after buffer initialization.\r\n");
    xil_printf("DISPLAY_MODE=1280x720p60, scanout=844x422, COMPACT_EXP_V1.\r\n");
    xil_printf("NETWORK_RANGE_BINS=0..1023; POWER_READ_GUARD=4MiB; MODEL=COMPACT_WEAKFIX_Q16.\r\n");
    return 0;
}
