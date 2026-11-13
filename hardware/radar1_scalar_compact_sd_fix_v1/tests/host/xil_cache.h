#ifndef HOST_XIL_CACHE_H
#define HOST_XIL_CACHE_H
/* Host memory disk has no device DMA/cache ownership. */
#include "xil_types.h"
void Xil_DCacheFlushRange(INTPTR address, u32 length);
#endif
