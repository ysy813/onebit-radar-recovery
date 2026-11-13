set dir [file dirname [file normalize [info script]]]
set modes {raw_imaging onebit_bypass onebit_network onebit_network_storage}
if {![info exists test_mode] || $test_mode ni $modes} {error "Run a program_* script"}
set bit [file join $dir design_1_wrapper.bit]
set elf [file join $dir ${test_mode}.elf]
set psu [file join $dir psu_init.tcl]
set manifest [file join $dir BUILD_READY.json]
foreach path [list $bit $elf $psu $manifest] {
 if {![file exists $path]} {error "Incomplete network package: $path"}
}
set fd [open $manifest r];set contents [read $fd];close $fd
if {![regexp {"ready_for_board_test"[[:space:]]*:[[:space:]]*true} $contents]} {error "Package has not passed release checks"}
puts "RADAR1 SCALAR COMPACT EXP V1: $test_mode"
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
puts "HDMI: standard 1280x720p60; full radar image reduced to 844x422 for display."
puts "Check UART IMAGING_INIT_PASS and NETWORK_REQUEST before triggering radar."
puts "Press PL_KEY2 once (>50 ms), wait 5 sec, then Trigger Frame."
puts "Use the existing 1024 samples, 512 chirps, 4 RX radar profile."
puts "NET done must increase; fault must remain 0. image_skip counts whole image frames."
puts "Stop Frame before reprogramming. In storage mode wait for final RESULT before powering off."
disconnect
