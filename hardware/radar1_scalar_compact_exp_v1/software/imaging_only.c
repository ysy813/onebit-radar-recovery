#include "xil_cache.h"
#include "xil_printf.h"
#include "branch_control.h"
#include "sleep.h"
#ifndef IMAGE_ONEBIT
#define IMAGE_ONEBIT 0U
#endif
extern int initialize_imaging_buffers(void);
int main(void) {
    Xil_DCacheDisable();
    Xil_ICacheDisable();
    if (initialize_imaging_buffers() != 0 || enable_capture_mode(1U, IMAGE_ONEBIT) != 0) {
        xil_printf("IMAGING_ONLY_INIT_FAIL.\r\n");
        for (;;) {}
    }
    xil_printf("IMAGING_ONLY_READY: storage branch disabled; DMA/SD not started.\r\n");
    xil_printf("PL_KEY2 once (>50 ms), wait 5 sec, then Trigger Frame once.\r\n");
    xil_printf("1024 ADC samples, 512 chirps, 4 RX, Frames=60 for first test (0=continuous), Periodicity=500 ms.\r\n");
    xil_printf("Use Stop Frame before any reprogramming.\r\n");
    for (;;) {usleep(1000000);network_log(0);}
}
