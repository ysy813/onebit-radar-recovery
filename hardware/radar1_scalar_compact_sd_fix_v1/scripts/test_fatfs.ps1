$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$gcc='C:\Xilinx\Vitis_HLS\2022.1\tps\mingw\8.3.0\win64.o\nt\bin\gcc.exe'
$build=Join-Path $root 'test_build'
New-Item -ItemType Directory -Force $build | Out-Null
$includes=@("-I$root\tests\host","-I$root\bsp\include","-I$root\software")
# Vendor source has pre-existing diagnostics; keep strict warnings on our code.
& $gcc -O2 @includes -c "$root\tests\vendor\ff.c" -o "$build\ff.o"
if($LASTEXITCODE){throw 'Host FatFs compile failed'}
foreach($source in @('software\sd_space.c','tests\fatfs_regression.c')){
    $name=[IO.Path]::GetFileNameWithoutExtension($source)
    & $gcc -Wall -Wextra -Werror -O2 @includes -c (Join-Path $root $source) -o "$build\$name.o"
    if($LASTEXITCODE){throw "Host compile failed: $source"}
}
& $gcc -static -o "$build\fatfs_regression.exe" "$build\ff.o" "$build\sd_space.o" "$build\fatfs_regression.o"
if($LASTEXITCODE){throw 'Host FatFs link failed'}
& "$build\fatfs_regression.exe" | Tee-Object -FilePath "$root\reports\fatfs_regression.log"
if($LASTEXITCODE){throw 'Host FatFs regression failed'}
