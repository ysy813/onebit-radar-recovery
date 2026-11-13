#include <stdint.h>
#include "sd_space.h"
#include "xil_printf.h"

#if FF_DEFINED != 63463 || FF_FS_READONLY || FF_MAX_SS != 512 || FF_MIN_SS != 512
#error This startup recount requires the pinned writable FatFs R0.13b BSP.
#endif

int sd_prepare_space(FATFS *volume, UINT block_bytes) {
    DWORD cached, counted = 0;
    FATFS *actual = NULL;
    FRESULT result;
    uint64_t free_bytes, required_bytes;
    uint32_t cluster_bytes;
    if (volume == NULL || volume->fs_type < FS_FAT12 ||
        volume->fs_type > FS_FAT32 || volume->n_fatent < 3U ||
        volume->csize == 0U || block_bytes == 0U) {
        xil_printf("FAIL: SD invalid/unhandled mounted volume.\r\n");
        return -1;
    }
    cluster_bytes = (uint32_t)volume->csize * FF_MAX_SS;
    cached = volume->free_clst;
    xil_printf("SD_MOUNT: type=%u (3=FAT32) cluster_bytes=%u total_clusters=%u cached_free=%u.\r\n",
        (unsigned)volume->fs_type, (unsigned)cluster_bytes,
        (unsigned)(volume->n_fatent - 2U), (unsigned)cached);
    xil_printf("SD_SCAN: recounting actual FAT allocation before capture; please wait.\r\n");
    /* In this pinned FatFs, f_getfree otherwise returns any in-range cached
     * count, including a stale zero imported from FAT32 FSInfo. Invalidate
     * only the RAM hint before the API call; do not edit raw card sectors.
     * A successful scan updates the RAM count and schedules ordinary FSInfo
     * synchronization through FatFs. This happens once before capture. */
    volume->free_clst = 0xFFFFFFFFU;
    result = f_getfree("0:/", &counted, &actual);
    if (result != FR_OK || actual != volume || counted > volume->n_fatent - 2U) {
        xil_printf("FAIL: SD FAT scan result=%d; capture not started.\r\n", result);
        return -1;
    }
    free_bytes = (uint64_t)counted * cluster_bytes;
    /* Allow a full raw block plus clusters for CSV and directory growth. */
    required_bytes = (uint64_t)block_bytes + 3ULL * cluster_bytes;
    xil_printf("SD_SPACE: counted_free=%u free_MiB=%u raw_blocks_available=%u.\r\n",
        (unsigned)counted, (unsigned)(free_bytes >> 20),
        (unsigned)(free_bytes / block_bytes));
    if (cached != 0xFFFFFFFFU && cached != counted) {
        xil_printf("SD_FSINFO_STALE: cached=%u actual=%u; using scanned count.\r\n",
            (unsigned)cached, (unsigned)counted);
    }
    if (free_bytes < required_bytes) {
        xil_printf("FAIL: SD actual free space insufficient for one raw block and metadata; capture not started.\r\n");
        return -1;
    }
    xil_printf("SD_SPACE_PASS: FAT allocation verified.\r\n");
    return 0;
}
