#ifndef RADAR_SD_SPACE_H
#define RADAR_SD_SPACE_H
#include "ff.h"

/* Call once, after mounting and before opening files or starting capture. */
int sd_prepare_space(FATFS *volume, UINT block_bytes);
#endif
