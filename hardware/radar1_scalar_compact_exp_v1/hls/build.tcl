set root [file dirname [file normalize [info script]]]
cd $root
open_project -reset project
set_top scalar_gain
add_files [file join $root scalar_compact.cpp] -cflags "-I$root -O2"
add_files -tb [file join $root compact_testbench.cpp] -cflags "-I$root -O2"
open_solution -reset solution -flow_target vivado
set_part {xczu4ev-sfvc784-1-i}
# Schedule with margin at 8 ns; the integrated IP runs at 100 MHz (10 ns).
create_clock -period 8 -name default
config_rtl -reset control -reset_level low
config_compile -name_max_length 40
config_interface -m_axi_addr64=false
csim_design -argv [file join $root ../numeric]
csynth_design
export_design -format ip_catalog -vendor local -library radar -version 1.0
exit
