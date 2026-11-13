set root [file dirname [file dirname [file normalize [info script]]]]
open_project [file join $root project imaging_storage.xpr]
set synth [get_runs network_synth]
if {[get_property NEEDS_REFRESH $synth]} {reset_run $synth}
launch_runs $synth -jobs 4
wait_on_run $synth
if {![string match "*synth_design Complete*" [get_property STATUS $synth]]} {error "Network system synthesis failed"}
if {[get_property NEEDS_REFRESH [get_runs network_impl]]} {reset_run network_impl}
launch_runs network_impl -to_step write_bitstream -jobs 4
wait_on_run network_impl
if {![string match "*write_bitstream Complete*" [get_property STATUS [get_runs network_impl]]]} {error "Network system implementation failed"}
open_run network_impl
set out [file join $root reports]
report_timing_summary -max_paths 10 -file [file join $out timing_summary.rpt]
report_utilization -file [file join $out utilization.rpt]
report_route_status -file [file join $out route_status.rpt]
report_drc -file [file join $out drc.rpt]
report_cdc -file [file join $out cdc.rpt]
file copy -force [file join [get_property DIRECTORY [get_runs network_impl]] design_1_wrapper.bit] [file join $root pkg design_1_wrapper.bit]
write_debug_probes -force [file join $root pkg design_1_wrapper.ltx]
write_hw_platform -fixed -include_bit -force [file join $root pkg scalar_network.xsa]
puts NETWORK_HARDWARE_BUILT
close_project
exit
