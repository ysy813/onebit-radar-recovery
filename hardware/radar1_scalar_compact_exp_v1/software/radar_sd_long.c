/* v3: non-cyclic SG ring. A completed buffer remains CPU-owned until its
 * frozen snapshot has been written. Hardware may not overwrite CPU-owned
 * buffers. The ring absorbs short SD stalls, never hides sustained overload.
 * Each raw file is <=256 MiB; CSV stores block hashes and measured timings.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "xparameters.h"
#include "xil_printf.h"
#include "xil_cache.h"
#include "xil_mmu.h"
#include "xil_io.h"
#include "xaxidma.h"
#include "xaxidma_hw.h"
#include "xtime_l.h"
#include "sleep.h"
#include "ff.h"
#include "branch_control.h"

#ifndef BRANCH_MODE
#define BRANCH_MODE 3U
#endif
#ifndef IMAGE_ONEBIT
#define IMAGE_ONEBIT 0U
#endif
#if BRANCH_MODE != 2 && BRANCH_MODE != 3
#error This SD application supports storage-only (2) or simultaneous (3).
#endif

#ifdef ONEBIT_MODE_BUILD
#if XPAR_AXIDMA_0_SG_INCLUDE_STSCNTRL_STRM != 0
#error One-bit build requires the matching BSP with DMA status stream disabled.
#endif
#define VERSION "radar1-scalar-compact-exp-v1"
#elif defined(STORAGE_STATUS_FIX)
#if XPAR_AXIDMA_0_SG_INCLUDE_STSCNTRL_STRM != 0
#error Raw capture requires the matching BSP with the unused DMA status stream disabled.
#endif
#define VERSION "imaging-storage-v3.2-statusfix-20261019"
#else
#define VERSION "imaging-storage-v3.1-migration-20261019"
#endif
extern int initialize_imaging_buffers(void);
#define FRAME_BYTES (2U * 1024U * 1024U)
#define FRAME_WORDS (FRAME_BYTES / 4U)
#define RING_COUNT 64U
#define BD_BASE 0x27F00000U
#define DATA_BASE 0x28000000U
#define STATUS_BASE 0xA0010000U
#define CHUNK_BYTES (256U * 1024U)
#define FILE_FRAMES 128U
#define MAX_FILES 999U
/* First acceptance test: 600 blocks / 10 min at 1000 ms. Zero = until stop,
 * card space exhausted, or integrity fault. No storage file is overwritten. */
#ifndef RECORD_LIMIT
#define RECORD_LIMIT 600U
#endif
#ifndef PERIOD_MS
#define PERIOD_MS 1000U
#endif
#define MAX_RUN 8192U
#define MANIFEST_SYNC_FRAMES 8U

typedef struct { uint32_t freeze, data_write, data_sync, metadata, cycle; } Timing;
static Timing timing;

typedef struct { uint32_t sum, xor_value, fnv, transitions, max_run; } Digest;
typedef struct { char path[32]; uint32_t frames; } SavedFile;
static XAxiDma dma;
static XAxiDma_BdRing *ring;
static FATFS fs;
static FIL output, manifest;
static char manifest_path[32], output_path[32];
static SavedFile files[MAX_FILES];
static uint32_t file_count, file_frames, total_frames, max_pending;
static Digest expected[MAX_FILES * FILE_FRAMES];
static uint32_t expected_count;
static uint32_t staging[FRAME_WORDS] __attribute__((aligned(64)));
static BYTE readback[CHUNK_BYTES] __attribute__((aligned(64)));
static int output_open, manifest_open, mounted, dma_initialized;
static int acquisition_error;
#ifdef STORAGE_STATUS_FIX
static int ring_created;
static void dump_dma_state(const char *reason) {
    uint32_t index;
    const UINTPTR channel=dma.RegBase + XAXIDMA_RX_OFFSET;
    const uint32_t status=XAxiDma_ReadReg(channel,XAXIDMA_SR_OFFSET);
    xil_printf("DMA_DIAG %s: CR=%08X SR=%08X errors=%08X faults=%X branch=%u.\r\n",
        reason, XAxiDma_ReadReg(channel,XAXIDMA_CR_OFFSET),status,
        status & XAXIDMA_ERR_ALL_MASK,Xil_In32(STATUS_BASE)&15U,
        Xil_In32(BRANCH_CONTROL_ADDR)&3U);
    xil_printf("DMA_DESC: CUR=%08X:%08X TAIL=%08X:%08X.\r\n",
        XAxiDma_ReadReg(channel,XAXIDMA_CDESC_MSB_OFFSET),XAxiDma_ReadReg(channel,XAXIDMA_CDESC_OFFSET),
        XAxiDma_ReadReg(channel,XAXIDMA_TDESC_MSB_OFFSET),XAxiDma_ReadReg(channel,XAXIDMA_TDESC_OFFSET));
    if (!ring_created) return;
    xil_printf("DMA_RING: Hw=%d Free=%d Pre=%d Post=%d head=%08X tail=%08X.\r\n",
        ring->HwCnt,ring->FreeCnt,ring->PreCnt,ring->PostCnt,
        (uint32_t)(UINTPTR)ring->HwHead,(uint32_t)(UINTPTR)ring->HwTail);
    for (index=0;index<4U;++index) {
        XAxiDma_Bd *bd=(XAxiDma_Bd *)(UINTPTR)(BD_BASE+index*XAXIDMA_BD_MINIMUM_ALIGNMENT);
        xil_printf("DMA_BD%u: next=%08X buf=%08X ctrl=%08X sts=%08X.\r\n",index,
            XAxiDma_BdRead(bd,XAXIDMA_BD_NDESC_OFFSET),XAxiDma_BdRead(bd,XAXIDMA_BD_BUFA_OFFSET),
            XAxiDma_BdRead(bd,XAXIDMA_BD_CTRL_LEN_OFFSET),XAxiDma_BdRead(bd,XAXIDMA_BD_STS_OFFSET));
    }
    Xil_DCacheInvalidateRange(DATA_BASE,64U);
    xil_printf("DMA_POOL0: %08X %08X %08X %08X (live sample, not an integrity verdict).\r\n",
        Xil_In32(DATA_BASE),Xil_In32(DATA_BASE+4U),Xil_In32(DATA_BASE+8U),Xil_In32(DATA_BASE+12U));
}
#endif

static uint32_t milliseconds(XTime start, XTime end) {
    return (uint32_t)(((uint64_t)(end-start)*1000ULL)/COUNTS_PER_SECOND);
}
static uint32_t sr(void) {
    return XAxiDma_ReadReg(dma.RegBase + XAXIDMA_RX_OFFSET, XAXIDMA_SR_OFFSET);
}
static uint32_t faults(void) { return Xil_In32(STATUS_BASE) & 15U; }
static int health(void) {
    uint32_t flags = faults();
    if (flags || (sr() & XAXIDMA_ERR_ALL_MASK)) {
        xil_printf("FAIL: input faults=0x%X DMA SR=0x%08X.\r\n", flags, sr());
        xil_printf("fault bits: 0=UDP sequence, 1=ADC byte offset, 2=FIFO overflow, 3=missing beginning.\r\n");
        acquisition_error = 1;
        return -1;
    }
    /* Once every submitted descriptor has completed, there is no spare
     * receive buffer. Stop explicitly: Ethernet cannot be backpressured. */
    if (ring->HwCnt && XAxiDma_BdHwCompleted(ring->HwTail)) {
        xil_printf("FAIL: all %u receive buffers exhausted; SD cannot keep up.\r\n", RING_COUNT);
        acquisition_error = 1;
        return -1;
    }
    return 0;
}
static uint32_t pending(void) {
    uint32_t count = 0;
    XAxiDma_Bd *bd = ring->HwHead;
    while (count < (uint32_t)ring->HwCnt && XAxiDma_BdHwCompleted(bd)) {
        ++count;
        bd = (XAxiDma_Bd *)XAxiDma_BdRingNext(ring, bd);
    }
    if (count > max_pending) max_pending = count;
    return count;
}
static int setup_ring(void) {
    XAxiDma_Config *config = XAxiDma_LookupConfig(XPAR_AXIDMA_0_DEVICE_ID);
    XAxiDma_Bd template_bd, *head, *bd;
    uint32_t index;
    if (!config || !config->HasSg) {
        xil_printf("FAIL: v3 requires its SG BSP and SG bitstream.\r\n");
        return -1;
    }
    if (XAxiDma_CfgInitialize(&dma, config) != XST_SUCCESS) return -1;
    dma_initialized = 1;
    if (!(sr() & 0x00000008U)) { /* DMASR.SGIncld, PG021 */
        xil_printf("FAIL: hardware is not SG DMA.\r\n"); return -1;
    }
    ring = XAxiDma_GetRxRing(&dma);
    XAxiDma_BdRingIntDisable(ring, XAXIDMA_IRQ_ALL_MASK);
    if (XAxiDma_BdRingCreate(ring, BD_BASE, BD_BASE,
                            XAXIDMA_BD_MINIMUM_ALIGNMENT, RING_COUNT) != XST_SUCCESS) return -1;
#ifdef STORAGE_STATUS_FIX
    ring_created=1;
#endif
    XAxiDma_BdClear(&template_bd);
    if (XAxiDma_BdRingClone(ring, &template_bd) != XST_SUCCESS) return -1;
    if (XAxiDma_BdRingAlloc(ring, RING_COUNT, &head) != XST_SUCCESS) return -1;
    bd = head;
    for (index=0; index<RING_COUNT; ++index) {
        uint32_t address = DATA_BASE + index*FRAME_BYTES;
        if (XAxiDma_BdSetBufAddr(bd, address) != XST_SUCCESS ||
            XAxiDma_BdSetLength(bd, FRAME_BYTES, ring->MaxTransferLen) != XST_SUCCESS) return -1;
        XAxiDma_BdSetCtrl(bd, 0);
        XAxiDma_BdSetId(bd, address);
        bd = (XAxiDma_Bd *)XAxiDma_BdRingNext(ring, bd);
    }
    if (XAxiDma_BdRingToHw(ring, RING_COUNT, head) != XST_SUCCESS ||
        XAxiDma_BdRingStart(ring) != XST_SUCCESS) return -1;
    xil_printf("SG DMA armed: 64 buffers, 128 MiB, non-cyclic ownership.\r\n");
#ifdef STORAGE_STATUS_FIX
    xil_printf("DMA_CONFIG: control/status stream disabled (BSP=0); raw capture needs no status packets.\r\n");
    dump_dma_state("ARMED");
#endif
    return 0;
}
static int wait_block(XAxiDma_Bd **bd) {
    XTime start, now;
    uint32_t limit = total_frames ? 5000U : 60000U;
    XTime_GetTime(&start);
    for (;;) {
        if (health()) return -1;
        if (XAxiDma_BdRingFromHw(ring, 1, bd) == 1) return 0;
        XTime_GetTime(&now);
        if (milliseconds(start, now) >= limit) {
            xil_printf("No complete block for %u ms; stopping and draining saved data.\r\n", limit);
            /* User Stop Frame after some data is a clean stop. Partial
             * final 2 MiB block is intentionally not appended. */
            return total_frames ? 1 : -1;
        }
        usleep(1000);
    }
}
static int release_block(XAxiDma_Bd *done) {
    UINTPTR address = XAxiDma_BdGetId(done);
    XAxiDma_Bd *fresh;
    if (XAxiDma_BdRingFree(ring, 1, done) != XST_SUCCESS ||
        XAxiDma_BdRingAlloc(ring, 1, &fresh) != XST_SUCCESS) return -1;
    XAxiDma_BdWrite(fresh, XAXIDMA_BD_STS_OFFSET, 0);
    if (XAxiDma_BdSetBufAddr(fresh, address) != XST_SUCCESS ||
        XAxiDma_BdSetLength(fresh, FRAME_BYTES, ring->MaxTransferLen) != XST_SUCCESS) return -1;
    XAxiDma_BdSetCtrl(fresh, 0);
    XAxiDma_BdSetId(fresh, address);
    return XAxiDma_BdRingToHw(ring, 1, fresh) == XST_SUCCESS ? 0 : -1;
}
static Digest digest(const uint32_t *words) {
    Digest d = {0,0,2166136261U,0,0};
    uint32_t index, last=0, run=0;
    for (index=0; index<FRAME_WORDS; ++index) {
        uint32_t value=words[index];
        d.sum += value; d.xor_value ^= value;
        d.fnv=(d.fnv ^ value)*16777619U;
        if (index && value!=last) ++d.transitions;
        run=(!index || value!=last) ? 1U : run+1U;
        if (run>d.max_run) d.max_run=run;
        last=value;
    }
    return d;
}
static int freeze_block(XAxiDma_Bd *bd, Digest *d) {
    uint32_t status = XAxiDma_BdGetSts(bd);
    uint32_t length = XAxiDma_BdGetActualLength(bd, ring->MaxTransferLen);
    const uint32_t *source=(const uint32_t *)(UINTPTR)XAxiDma_BdGetId(bd);
    Digest before;
    if ((status & XAXIDMA_BD_STS_ALL_ERR_MASK) || length!=FRAME_BYTES ||
        !(status & XAXIDMA_BD_STS_RXSOF_MASK) || !(status & XAXIDMA_BD_STS_RXEOF_MASK)) {
        xil_printf("FAIL: descriptor status=%08X length=%u.\r\n",status,length); return -1;
    }
    /* DMA has completed and this descriptor is CPU-owned. Pool buffers are
     * read-only to the CPU; invalidate stale lines before reading a new DMA
     * generation. Descriptors themselves reside in a noncacheable 2 MiB block. */
    Xil_DCacheInvalidateRange((UINTPTR)source, FRAME_BYTES);
    before=digest(source);
    memcpy(staging, source, FRAME_BYTES);
    *d=digest(staging);
    if (before.sum!=d->sum || before.xor_value!=d->xor_value || before.fnv!=d->fnv ||
        !d->transitions || d->max_run>MAX_RUN) {
        xil_printf("FAIL: frozen block integrity or constant-data test.\r\n"); return -1;
    }
    /* SD controller reads RAM, not dirty CPU cache lines. The BSP SD driver
     * also flushes writes; explicit flushing keeps staging ownership clear. */
    Xil_DCacheFlushRange((UINTPTR)staging, FRAME_BYTES);
    return 0;
}
static int write_exact(FIL *file, const void *data, UINT size) {
    UINT written=0;
    FRESULT result=f_write(file,data,size,&written);
    if (result!=FR_OK || written!=size) {
        xil_printf("FAIL: SD write result=%d requested=%u actual=%u.\r\n",result,size,written);
        return -1;
    }
    return 0;
}
static int make_manifest(void) {
    uint32_t number;
    for (number=1; number<=MAX_FILES; ++number) {
        FRESULT result;
        snprintf(manifest_path,sizeof(manifest_path),"0:/RUN%05u.CSV",number);
        result=f_open(&manifest,manifest_path,FA_WRITE|FA_CREATE_NEW);
        if (result==FR_EXIST) continue;
        if (result!=FR_OK) return -1;
        manifest_open=1;
        {
            const char *header="file,block,global_block,bytes,sum32,xor32,fnv32,write_sync_ms,pending,input_faults,freeze_ms,data_write_ms,data_sync_ms\r\n";
            return write_exact(&manifest,header,(UINT)strlen(header));
        }
    }
    return -1;
}
static int open_segment(void) {
    uint32_t number;
    if (file_count==MAX_FILES) return -1;
    for (number=1; number<=MAX_FILES; ++number) {
        FRESULT result;
        snprintf(output_path,sizeof(output_path),"0:/LNG%05u.BIN",number);
        result=f_open(&output,output_path,FA_WRITE|FA_CREATE_NEW);
        if (result==FR_EXIST) continue;
        if (result!=FR_OK) return -1;
        output_open=1; file_frames=0;
        strcpy(files[file_count].path,output_path);
        files[file_count].frames=0;
        ++file_count;
        xil_printf("New segment: %s, max=256 MiB.\r\n",output_path);
        return 0;
    }
    return -1;
}
static int close_segment(void) {
    FRESULT result;
    if (!output_open) return 0;
    result=f_close(&output); output_open=0;
    return result==FR_OK ? 0 : -1;
}
static int store_block(const Digest *d, uint32_t *write_ms) {
    uint32_t offset, queued;
    char line[240];
    XTime start,end,write_end,sync_end;
    if (!output_open && open_segment()) return -1;
    XTime_GetTime(&start);
    for (offset=0; offset<FRAME_BYTES; offset+=CHUNK_BYTES) {
        if (health() || write_exact(&output,(BYTE *)staging+offset,CHUNK_BYTES)) return -1;
    }
    XTime_GetTime(&write_end);
    if (f_sync(&output)!=FR_OK) return -1;
    XTime_GetTime(&sync_end);
    *write_ms=milliseconds(start,sync_end);
    timing.data_write=milliseconds(start,write_end);
    timing.data_sync=milliseconds(write_end,sync_end);
    if (health()) return -1;
    queued=pending();
    XTime_GetTime(&start);
    snprintf(line,sizeof(line),"%s,%u,%u,%u,%08X,%08X,%08X,%u,%u,%u,%u,%u,%u\r\n",
             output_path+3,file_frames,total_frames,FRAME_BYTES,d->sum,d->xor_value,d->fnv,
             *write_ms,queued,faults(),timing.freeze,timing.data_write,timing.data_sync);
    if (write_exact(&manifest,line,(UINT)strlen(line))) return -1;
    /* BIN is synced every block; CSV is synced every 8 blocks and on close.
     * This avoids switching between two FAT updates for every incoming frame.
     * Unexpected power loss may leave up to 7 BIN blocks without CSV rows. */
    if ((total_frames+1U)%MANIFEST_SYNC_FRAMES==0 && f_sync(&manifest)!=FR_OK) return -1;
    XTime_GetTime(&end); timing.metadata=milliseconds(start,end);
    expected[expected_count++]=*d;
    ++file_frames; ++total_frames;
    files[file_count-1].frames=file_frames;
    if (file_frames==FILE_FRAMES && close_segment()) return -1;
    return 0;
}
static int verify_files(void) {
    uint32_t f,b,entry=0;
    for (f=0; f<file_count; ++f) {
        FIL input;
        if (f_open(&input,files[f].path,FA_READ)!=FR_OK) return -1;
        if (f_size(&input)!=(FSIZE_t)files[f].frames*FRAME_BYTES) {
            f_close(&input); return -1;
        }
        for (b=0; b<files[f].frames; ++b) {
            uint32_t offset,i;
            Digest actual={0,0,2166136261U,0,0};
            for (offset=0; offset<FRAME_BYTES; offset+=CHUNK_BYTES) {
                UINT count;
                if (f_read(&input,readback,CHUNK_BYTES,&count)!=FR_OK || count!=CHUNK_BYTES) {
                    f_close(&input); return -1;
                }
                for (i=0; i<CHUNK_BYTES; i+=4) {
                    uint32_t word=(uint32_t)readback[i] | (uint32_t)readback[i+1]<<8 |
                                  (uint32_t)readback[i+2]<<16 | (uint32_t)readback[i+3]<<24;
                    actual.sum+=word; actual.xor_value^=word;
                    actual.fnv=(actual.fnv ^ word)*16777619U;
                }
            }
            if (actual.sum!=expected[entry].sum || actual.xor_value!=expected[entry].xor_value ||
                actual.fnv!=expected[entry].fnv) {
                xil_printf("FAIL: readback file=%s block=%u.\r\n",files[f].path,b);
                f_close(&input); return -1;
            }
            ++entry;
        }
        if (f_close(&input)!=FR_OK) return -1;
        xil_printf("Readback PASS: %s, blocks=%u.\r\n",files[f].path,files[f].frames);
    }
    return entry==expected_count ? 0 : -1;
}
int main(void) {
    uint32_t max_write=0;
    int result=-1, verified=-1;
    XTime record_start,record_end;
    uint64_t busy_ms=0;
    Xil_DCacheDisable();
#if BRANCH_MODE == 3
    if (initialize_imaging_buffers() != 0) {
        xil_printf("FAIL: imaging initialization; DMA/SD not started.\r\n");
        return -1;
    }
#else
    xil_printf("STORAGE_ONLY: imaging input branch disabled; no AQ_AR/display initialization.\r\n");
#endif
    Xil_SetTlbAttributes(BD_BASE, NORM_NONCACHE);
    Xil_DCacheEnable();
    Xil_ICacheEnable();
    xil_printf("\r\nBuild: %s, period expectation=%u ms, limit=%u blocks (0=continuous).\r\n",VERSION,PERIOD_MS,RECORD_LIMIT);
    if (f_mount(&fs,"0:/",1)!=FR_OK) goto finish;
    mounted=1;
    if (make_manifest() || open_segment() || setup_ring()) goto finish;
    if (enable_capture_mode(BRANCH_MODE, IMAGE_ONEBIT) != 0) goto finish;
    xil_printf("ACTION: PL_KEY2 once, wait 5 sec, then Trigger Frame. Frames=60 for first test (0=continuous), Periodicity=%u ms, click Set.\r\n",PERIOD_MS);
    xil_printf("For continuous mode, Stop Frame in Studio; do not cut power to request a clean stop.\r\n");
    XTime_GetTime(&record_start);
    for (;;) {
        XAxiDma_Bd *bd;
        Digest d;
        uint32_t write_ms;
        int wait_result;
        XTime busy_start,freeze_end,busy_end;
#if RECORD_LIMIT > 0
        if (total_frames>=RECORD_LIMIT) { result=0; break; }
#endif
        network_log(0);
        wait_result=wait_block(&bd);
        if (wait_result) {
#if RECORD_LIMIT > 0
            xil_printf("FAIL: finite test ended early, stored=%u expected=%u.\r\n",total_frames,RECORD_LIMIT);
            result=-1;
#else
            result=wait_result==1 ? 0 : -1;
#endif
            break;
        }
        XTime_GetTime(&busy_start);
        if (freeze_block(bd,&d)) break;
        XTime_GetTime(&freeze_end); timing.freeze=milliseconds(busy_start,freeze_end);
        if (store_block(&d,&write_ms) || health() || release_block(bd)) break;
        XTime_GetTime(&busy_end); timing.cycle=milliseconds(busy_start,busy_end);
        busy_ms+=timing.cycle;
        if (write_ms>max_write) max_write=write_ms;
        if (total_frames%16==0 || total_frames==1) {
            xil_printf("Stored=%u files=%u pending=%u/64 max_pending=%u write=%u ms max_write=%u faults=%X fnv=%08X.\r\n",
                       total_frames,file_count,pending(),max_pending,write_ms,max_write,faults(),d.fnv);
            xil_printf("PROFILE: freeze=%u write=%u sync=%u csv=%u cycle=%u avg_busy=%u ms.\r\n",
                       timing.freeze,timing.data_write,timing.data_sync,timing.metadata,
                       timing.cycle,(uint32_t)(busy_ms/total_frames));
            if (busy_ms/total_frames >= PERIOD_MS)
                xil_printf("WARNING: measured processing average >= %u ms; increase radar Periodicity.\r\n",PERIOD_MS);
        }
    }
    XTime_GetTime(&record_end);
    network_log(1);
    xil_printf("Recording ended: %u blocks, elapsed=%u ms. Click Stop Frame now.\r\n",total_frames,milliseconds(record_start,record_end));
finish:
    if (dma_initialized) {
        uint32_t limit=1000;
#ifdef STORAGE_STATUS_FIX
        /* Preserve the evidence before Reset clears DMA state. Input faults
         * remain fatal: neither overflow nor missing beginning is masked. */
        dump_dma_state("BEFORE_RESET");
#endif
        XAxiDma_Reset(&dma);
        while (limit-- && !XAxiDma_ResetIsDone(&dma)) usleep(1000);
        if (!XAxiDma_ResetIsDone(&dma)) result=-1;
    }
    if (close_segment()) result=-1;
    if (manifest_open) {
        if (f_close(&manifest)!=FR_OK) result=-1;
        manifest_open=0;
    }
    if (mounted) {
        if (total_frames) { xil_printf("Verifying saved files...\r\n"); verified=verify_files(); }
        if (f_mount(NULL,"0:/",0)!=FR_OK) result=-1;
    }
    xil_printf("RESULT: %s, stored=%u blocks, files=%u, max_pending=%u, acquisition_error=%d.\r\n",
               result==0 && verified==0 && !acquisition_error ? "PASS" : "FAIL",
               total_frames,file_count,max_pending,acquisition_error);
    xil_printf("Manifest: %s. Partial files retained.\r\n",manifest_path);
    for (;;) { usleep(1000000); network_log(0); }
}
