/* Real BSP FatFs with a synthetic memory FAT32 disk. Never opens a device. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "ff.h"
#include "diskio.h"
#include "sd_space.h"

#define CLUSTERS 70000U
#define FAT_SECTORS (((CLUSTERS + 2U) * 4U + 511U) / 512U)
#define RESERVED 32U
#define DATA_SECTOR (RESERVED + 2U * FAT_SECTORS)
#define SECTORS (DATA_SECTOR + CLUSTERS)
#define BLOCK_BYTES (2U * 1024U * 1024U)
static BYTE *media;
static DWORD fail_read_sector = 0xFFFFFFFFU;
static unsigned writes;
static const char header[] = "file,block,global_block,bytes,sum32,xor32,fnv32,write_sync_ms,pending,input_faults,freeze_ms,data_write_ms,data_sync_ms\r\n";
static const char keeper[] = "ORIGINAL_KEPT";
#define CHECK(condition) do { if (!(condition)) { fprintf(stderr, "CHECK FAILED line=%d: %s\n", __LINE__, #condition); exit(1); } } while (0)

void xil_printf(const char *format, ...) {
    va_list args; va_start(args, format); vprintf(format, args); va_end(args);
}
void Xil_DCacheFlushRange(INTPTR address, u32 length) { (void)address; (void)length; }
DWORD get_fattime(void) { return (DWORD)((2026U - 1980U) << 25 | 11U << 21 | 3U << 16); }
DSTATUS disk_initialize(BYTE drive) { return drive == 0U ? 0U : STA_NOINIT; }
DSTATUS disk_status(BYTE drive) { return disk_initialize(drive); }
DRESULT disk_read(BYTE drive, BYTE *buffer, DWORD sector, UINT count) {
    if (drive != 0U || sector >= SECTORS || count > SECTORS - sector) return RES_PARERR;
    if (sector <= fail_read_sector && fail_read_sector < sector + count) return RES_ERROR;
    memcpy(buffer, media + (size_t)sector * 512U, (size_t)count * 512U);
    return RES_OK;
}
DRESULT disk_write(BYTE drive, const BYTE *buffer, DWORD sector, UINT count) {
    if (drive != 0U || sector >= SECTORS || count > SECTORS - sector) return RES_PARERR;
    memcpy(media + (size_t)sector * 512U, buffer, (size_t)count * 512U);
    ++writes;
    return RES_OK;
}
DRESULT disk_ioctl(BYTE drive, BYTE command, void *buffer) {
    if (drive != 0U) return RES_PARERR;
    switch (command) {
    case CTRL_SYNC: return RES_OK;
    case GET_SECTOR_COUNT: *(DWORD *)buffer = SECTORS; return RES_OK;
    case GET_SECTOR_SIZE: *(WORD *)buffer = 512U; return RES_OK;
    case GET_BLOCK_SIZE: *(DWORD *)buffer = 1U; return RES_OK;
    default: return RES_PARERR;
    }
}
static void put16(BYTE *p, uint16_t v) { p[0]=(BYTE)v; p[1]=(BYTE)(v>>8); }
static void put32(BYTE *p, uint32_t v) { put16(p,(uint16_t)v); put16(p+2,(uint16_t)(v>>16)); }
static uint32_t get32(const BYTE *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static void format_disk(uint32_t cached, int fullness) {
    BYTE *b, *fat, *info, *entry;
    uint32_t i;
    CHECK(f_mount(NULL,"0:/",0)==FR_OK);
    memset(media,0,(size_t)SECTORS*512U); writes=0; fail_read_sector=0xFFFFFFFFU;
    b=media;
    b[0]=0xEB; b[1]=0x58; b[2]=0x90;
    memcpy(b+3,"MSWIN4.1",8); put16(b+11,512); b[13]=1;
    put16(b+14,RESERVED); b[16]=2; b[21]=0xF8;
    put32(b+32,SECTORS); put32(b+36,FAT_SECTORS); put32(b+44,2);
    put16(b+48,1); put16(b+50,6); b[64]=0x80; b[66]=0x29;
    memcpy(b+82,"FAT32   ",8); put16(b+510,0xAA55);
    info=media+512; put32(info,0x41615252); put32(info+484,0x61417272);
    put32(info+488,cached); put32(info+492,3); put32(info+508,0xAA550000);
    memcpy(media+6U*512U,b,512); memcpy(media+7U*512U,info,512);
    fat=media+RESERVED*512U;
    put32(fat,0x0FFFFFF8); put32(fat+4,0x0FFFFFFF);
    put32(fat+8,0x0FFFFFFF); put32(fat+12,0x0FFFFFFF);
    if (fullness) for(i=4;i<CLUSTERS+2U;++i) put32(fat+i*4U,0x0FFFFFFF);
    if (fullness==2) put32(fat+4U*4U,0);
    memcpy(fat+FAT_SECTORS*512U,fat,FAT_SECTORS*512U);
    entry=media+DATA_SECTOR*512U;
    memcpy(entry,"KEEP    BIN",11); entry[11]=0x20; put16(entry+26,3);
    put32(entry+28,sizeof(keeper));
    memcpy(entry+512,keeper,sizeof(keeper));
}
static void check_keeper(void) {
    FIL file; char readback[sizeof(keeper)]; UINT count=0;
    CHECK(f_open(&file,"0:/KEEP.BIN",FA_READ)==FR_OK);
    CHECK(f_read(&file,readback,sizeof(readback),&count)==FR_OK);
    CHECK(count==sizeof(readback) && memcmp(readback,keeper,sizeof(keeper))==0);
    CHECK(f_close(&file)==FR_OK);
}
static void roundtrip(const char *name, const void *data, UINT size) {
    FIL file; UINT count=0; BYTE *buffer=malloc(size);
    CHECK(buffer!=NULL);
    CHECK(f_open(&file,name,FA_WRITE|FA_CREATE_NEW)==FR_OK);
    CHECK(f_write(&file,data,size,&count)==FR_OK && count==size);
    CHECK(f_sync(&file)==FR_OK); CHECK(f_close(&file)==FR_OK);
    CHECK(f_open(&file,name,FA_READ)==FR_OK && f_size(&file)==size);
    CHECK(f_read(&file,buffer,size,&count)==FR_OK && count==size);
    CHECK(memcmp(buffer,data,size)==0 && f_close(&file)==FR_OK);
    free(buffer);
}
int main(void) {
    FATFS fs, *queried=NULL; FIL file; UINT count; DWORD reported;
    BYTE *block; unsigned before; uint32_t i, remaining;
    media=malloc((size_t)SECTORS*512U); CHECK(media!=NULL);
    CHECK(sizeof(header)-1U==121U);
    format_disk(0,0);
    CHECK(f_mount(&fs,"0:/",1)==FR_OK && fs.fs_type==FS_FAT32);
    CHECK(f_getfree("0:/",&reported,&queried)==FR_OK && reported==0);
    CHECK(f_open(&file,"0:/BAD.CSV",FA_WRITE|FA_CREATE_NEW)==FR_OK);
    CHECK(f_write(&file,header,121,&count)==FR_OK && count==0);
    CHECK(f_close(&file)==FR_OK);
    puts("CASE_PASS original_stale_zero_reproduces_FR_OK_bw_0");
    check_keeper();
    before=writes;
    CHECK(sd_prepare_space(&fs,BLOCK_BYTES)==0 && fs.free_clst==CLUSTERS-2U);
    CHECK(writes==before); /* Startup scan itself does not write sectors. */
    roundtrip("0:/GOOD.CSV",header,121);
    block=malloc(BLOCK_BYTES); CHECK(block!=NULL);
    for(i=0;i<BLOCK_BYTES;++i) block[i]=(BYTE)(i*37U+11U);
    roundtrip("0:/RAW.BIN",block,BLOCK_BYTES); free(block);
    check_keeper();
    CHECK(memcmp(media+RESERVED*512U,media+(RESERVED+FAT_SECTORS)*512U,FAT_SECTORS*512U)==0);
    remaining=(uint32_t)fs.free_clst;
    CHECK(get32(media+512U+488U)==remaining && remaining>0U);
    CHECK(f_mount(NULL,"0:/",0)==FR_OK && f_mount(&fs,"0:/",1)==FR_OK);
    CHECK(fs.free_clst==remaining);
    puts("CASE_PASS recount_header_2MiB_readback_keeper_FAT_mirror_and_remount");
    format_disk(CLUSTERS-2U,0); CHECK(f_mount(&fs,"0:/",1)==FR_OK);
    CHECK(sd_prepare_space(&fs,BLOCK_BYTES)==0 && fs.free_clst==CLUSTERS-2U);
    puts("CASE_PASS already_correct_free_count");
    format_disk(CLUSTERS-1U,0); CHECK(f_mount(&fs,"0:/",1)==FR_OK);
    CHECK(sd_prepare_space(&fs,BLOCK_BYTES)==0 && fs.free_clst==CLUSTERS-2U);
    puts("CASE_PASS stale_nonzero_free_count");
    format_disk(0,1); CHECK(f_mount(&fs,"0:/",1)==FR_OK); before=writes;
    CHECK(sd_prepare_space(&fs,BLOCK_BYTES)!=0 && fs.free_clst==0 && writes==before);
    puts("CASE_PASS genuinely_full_refused_without_writes");
    format_disk(0,2); CHECK(f_mount(&fs,"0:/",1)==FR_OK); before=writes;
    CHECK(sd_prepare_space(&fs,BLOCK_BYTES)!=0 && fs.free_clst==1 && writes==before);
    puts("CASE_PASS insufficient_one_cluster_refused_without_writes");
    format_disk(0,0); CHECK(f_mount(&fs,"0:/",1)==FR_OK); before=writes;
    fail_read_sector=RESERVED+5U;
    CHECK(sd_prepare_space(&fs,BLOCK_BYTES)!=0 && writes==before);
    puts("CASE_PASS FAT_read_error_refused_without_writes");
    CHECK(f_mount(NULL,"0:/",0)==FR_OK); free(media);
    puts("FATFS_REGRESSION_PASS cases=7");
    return 0;
}
