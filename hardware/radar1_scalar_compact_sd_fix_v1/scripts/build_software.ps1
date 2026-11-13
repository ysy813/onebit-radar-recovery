$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$gcc='C:\Xilinx\Vitis\2022.1\gnu\aarch64\nt\aarch64-none\bin\aarch64-none-elf-gcc.exe'
$objcopy='C:\Xilinx\Vitis\2022.1\gnu\aarch64\nt\aarch64-none\bin\aarch64-none-elf-objcopy.exe'
$build=Join-Path $root 'software_build'
New-Item -ItemType Directory -Force $build | Out-Null
# Mark any earlier package ineligible until checks are run after this build.
$manifest=Join-Path $root 'pkg\BUILD_READY.json'
if(Test-Path -LiteralPath $manifest){
    '{"ready_for_board_test":false,"reason":"software rebuild awaiting checks"}' | Set-Content -Encoding utf8 -LiteralPath $manifest
}
Push-Location (Join-Path $root 'software')
try {
    & $objcopy -I binary -O elf64-littleaarch64 -B aarch64 aq_ar.bin (Join-Path $build 'aq_ar.o')
    if($LASTEXITCODE){throw 'AQ_AR conversion failed'}
    foreach($file in @('image_init','sd_space','radar_sd_long')){
        $argsCompile=@('-Wall','-Wextra','-Werror','-O2','-g3','-c',"-I$root\bsp\include",'-o',"$build\$file.o")
        if($file -eq 'radar_sd_long'){
            $argsCompile+=@('-DIMAGE_ONEBIT=1','-DNETWORK_ENABLE=1','-DPERIOD_MS=500','-DRECORD_LIMIT=0','-DSTORAGE_STATUS_FIX=1','-DONEBIT_MODE_BUILD=1','-DBRANCH_MODE=3')
        }
        & $gcc @argsCompile "$file.c"
        if($LASTEXITCODE){throw "compile failed: $file"}
    }
    & $gcc '-Wl,-T' "-Wl,$root\software\lscript.ld" "-Wl,-Map,$build\onebit_network_storage.map" "-L$root\bsp\lib" -o "$root\pkg\onebit_network_storage.elf" "$build\image_init.o" "$build\aq_ar.o" "$build\sd_space.o" "$build\radar_sd_long.o" '-Wl,--start-group' -lxilffs -lxil -lgcc -lc '-Wl,--end-group'
    if($LASTEXITCODE){throw 'link failed'}
} finally {Pop-Location}
Write-Output 'SD_FIX_SOFTWARE_BUILD_PASS'
