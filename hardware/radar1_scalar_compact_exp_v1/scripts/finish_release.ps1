param([switch]$SkipPackage)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPython='C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe'
$taskXsct='C:\Xilinx\Vitis\2022.1\bin\xsct.bat'
Push-Location $taskRoot
try {
 & $taskPython scripts\extract_psu.py
 if($LASTEXITCODE){throw 'PS initialization extraction failed'}
 if(Test-Path -LiteralPath 'vitis\scalar'){$taskPlatformScript='scripts\update_platform.tcl'}else{$taskPlatformScript='scripts\build_platform.tcl'}
 & $taskXsct $taskPlatformScript *> reports\final_platform_console.log
 if($LASTEXITCODE){throw 'Matching BSP generation failed'}
 & $PSScriptRoot\build_software.ps1 *> reports\final_software_console.log
 if(-not $SkipPackage){
  & $taskPython scripts\package_compact.py
  if($LASTEXITCODE){throw 'Release validation failed'}
 }
} finally {Pop-Location}
