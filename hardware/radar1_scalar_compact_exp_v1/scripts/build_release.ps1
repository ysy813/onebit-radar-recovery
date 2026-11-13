$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPython='C:\Users\yang\AppData\Local\Programs\Python\Python313\python.exe'
$taskVivado='C:\Xilinx\Vivado\2022.1\bin\vivado.bat'
$taskHls='C:\Xilinx\Vitis_HLS\2022.1\bin\vitis_hls.bat'
$taskXsct='C:\Xilinx\Vitis\2022.1\bin\xsct.bat'
if(Test-Path -LiteralPath (Join-Path $taskRoot 'radar1_scalar_compact_exp_v1_runtime.zip')){throw 'Published package exists; rebuild in another independent folder.'}
Push-Location $taskRoot
try {
 & $taskPython numeric\prepare_compact.py *> reports\prepare_numeric.log
 if($LASTEXITCODE){throw 'Numeric preparation failed'}
 & $taskHls -f hls\build.tcl *> reports\hls_console.log
 if(-not (Select-String -Quiet -Path hls\project\solution\csim\report\scalar_gain_csim.log -SimpleMatch 'HLS_CSIM_PASS')){throw 'HLS simulation failed'}
 if(-not (Test-Path hls\project\solution\impl\ip\component.xml)){throw 'HLS IP export failed'}
 & $taskPython numeric\prepare_rtl.py *> reports\prepare_rtl.log
 if($LASTEXITCODE){throw 'RTL preparation failed'}
 foreach($taskStage in @('compact','frame')){
  & $taskVivado -mode batch -source "scripts\simulate_$taskStage.tcl" -notrace *> "reports\simulate_$($taskStage)_console.log"
  if($LASTEXITCODE){throw "Simulation failed: $taskStage"}
 }
 & $taskVivado -mode batch -source scripts\build_compact.tcl -notrace *> reports\build_hardware_console.log
 if($LASTEXITCODE){throw 'Hardware build failed'}
 & $taskVivado -mode batch -source scripts\audit_final.tcl -notrace *> reports\final_audit_console.log
 if($LASTEXITCODE){throw 'Final hardware audit failed'}
 & $PSScriptRoot\finish_release.ps1
} finally {Pop-Location}
