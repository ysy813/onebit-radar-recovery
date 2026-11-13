set dir [file dirname [file normalize [info script]]]
if {![info exists test_mode] || $test_mode ne "onebit_network_storage"} {error "Use program_onebit_network_storage.tcl"}
set bit [file join $dir design_1_wrapper.bit]
set elf [file join $dir onebit_network_storage.elf]
set psu [file join $dir psu_init.tcl]
set manifest [file join $dir BUILD_READY.json]
foreach path [list $bit $elf $psu $manifest] {
    if {![file exists $path]} {error "Incomplete SD fix package: $path"}
}
set fd [open $manifest r];set contents [read $fd];close $fd
if {![regexp {"ready_for_board_test"[[:space:]]*:[[:space:]]*true} $contents]} {error "SD fix package has not passed release checks"}
puts "RADAR1 COMPACT SD FIX V1: network imaging plus raw storage"
puts "BIT: $bit"
puts "ELF: $elf"
connect
targets -set -nocase -filter {name =~ "*PSU*"}
rst -system
after 3000
source $psu
psu_init
after 1000
psu_ps_pl_isolation_removal
after 1000
psu_ps_pl_reset_config
after 1000
fpga -file $bit
after 2000
targets -set -nocase -filter {name =~ "*A53*#0*"}
rst -processor
dow $elf
con
puts "Wait for SD_SCAN, SD_SPACE_PASS, SD_MANIFEST_PASS and NETWORK_REQUEST=1 on UART."
puts "Only after ACTION: press PL_KEY2 once (>50 ms), wait 5 sec, Arm then Trigger Frame."
puts "Keep 1024 samples, 512 chirps, 4 RX, 500 ms for this storage regression."
puts "Stop Frame before reprogramming. Wait for final RESULT before removing the SD card."
disconnect
