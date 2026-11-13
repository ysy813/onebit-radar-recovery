$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$bsp=Join-Path $root 'vitis\scalar\export\scalar\sw\scalar\standalone_domain'
$gcc='C:\Xilinx\Vitis\2022.1\gnu\aarch64\nt\aarch64-none\bin\aarch64-none-elf-gcc.exe'
$objcopy='C:\Xilinx\Vitis\2022.1\gnu\aarch64\nt\aarch64-none\bin\aarch64-none-elf-objcopy.exe'
$build=Join-Path $root 'software_build'
$pkg=Join-Path $root 'pkg'
if(-not (Test-Path -LiteralPath (Join-Path $bsp 'bspinclude\include\xparameters.h'))){throw "BSP missing: $bsp"}
New-Item -ItemType Directory -Force $build,$pkg | Out-Null
Push-Location (Join-Path $root 'software')
try {
    & $objcopy -I binary -O elf64-littleaarch64 -B aarch64 aq_ar.bin (Join-Path $build 'aq_ar.o')
    if($LASTEXITCODE){throw 'AQ_AR conversion failed'}
    & $gcc -Wall -Wextra -Werror -O2 -g3 -c "-I$bsp\bspinclude\include" -o (Join-Path $build 'image_init.o') image_init.c
    if($LASTEXITCODE){throw 'image_init compile failed'}
    $cases=@(
        @{Name='raw_imaging'; Branch=1; Onebit=0; Network=0},
        @{Name='onebit_bypass'; Branch=1; Onebit=1; Network=0},
        @{Name='onebit_network'; Branch=1; Onebit=1; Network=1},
        @{Name='onebit_network_storage'; Branch=3; Onebit=1; Network=1}
    )
    foreach($case in $cases){
        $name=$case.Name
        $object=Join-Path $build "$name.o"
        $argsCompile=@('-Wall','-Wextra','-Werror','-O2','-g3','-c',"-DIMAGE_ONEBIT=$($case.Onebit)","-DNETWORK_ENABLE=$($case.Network)","-I$bsp\bspinclude\include",'-o',$object)
        if($case.Branch -eq 1){
            & $gcc @argsCompile imaging_only.c
        } else {
            & $gcc @argsCompile -DPERIOD_MS=500 -DRECORD_LIMIT=0 -DSTORAGE_STATUS_FIX=1 -DONEBIT_MODE_BUILD=1 "-DBRANCH_MODE=$($case.Branch)" radar_sd_long.c
        }
        if($LASTEXITCODE){throw "compile failed: $name"}
        & $gcc '-Wl,-T' "-Wl,$root\software\lscript.ld" "-Wl,-Map,$build\$name.map" "-L$bsp\bsplib\lib" -o (Join-Path $pkg "$name.elf") (Join-Path $build 'image_init.o') (Join-Path $build 'aq_ar.o') $object '-Wl,--start-group' -lxilffs -lxil -lgcc -lc '-Wl,--end-group'
        if($LASTEXITCODE){throw "link failed: $name"}
        Write-Output "ELF_READY $name"
    }
} finally {Pop-Location}
Write-Output SCALAR_SOFTWARE_PASS
