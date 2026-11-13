# Read-only audit of the implemented design. Never connects to hardware.
set root [file dirname [file dirname [file normalize [info script]]]]
open_project [file join $root project imaging_storage.xpr]
if {[get_property NEEDS_REFRESH [get_runs network_impl]]} {error "Implemented run is stale"}
open_run network_impl
foreach {name primitive} {serial_buffer BUFGCE divided_buffer BUFGCE_DIV} {
    if {[get_property REF_NAME [get_cells design_1_i/hdmi_serdes_clocks_0/inst/$name]] ne $primitive} {error "Unexpected HDMI clock buffer $name"}
}
set aligned [get_nets -of_objects [get_pins {design_1_i/hdmi_serdes_clocks_0/inst/serial_buffer/O design_1_i/hdmi_serdes_clocks_0/inst/divided_buffer/O}]]
if {[llength $aligned]!=2} {error "HDMI alignment requires two clock nets"}
foreach net $aligned {
    if {[get_property CLOCK_DELAY_GROUP $net] ne "HDMI_GEARBOX"} {error "HDMI clock delay group missing"}
    if {[get_property USER_CLOCK_ROOT $net] ne "X1Y3"} {error "HDMI serializer clock root missing"}
    puts "HDMI_CLOCK_ALIGNED $net [get_property CLOCK_DELAY_GROUP $net]"
}
if {[llength [get_cells -quiet -hier -filter {NAME =~ *u_dd_fifo/wr_g_sync*}]]} {error "Old broken display FIFO is still present"}
set fifo_cells [get_cells -quiet -hier -filter {NAME =~ *u_dd_fifo/fifo/*}]
puts "OPTIONAL_CAMERA_READ_FIFO_CELLS [llength $fifo_cells]"
set scanout_cells [get_cells -quiet -hier -filter {NAME =~ *display_0/inst/display_v1_0_M00_AXI_inst/scanout_fifo/*}]
if {![llength $scanout_cells]} {error "Verified radar scanout FIFO is absent"}
puts "RADAR_SCANOUT_FIFO_PRESENT [llength $scanout_cells]"
report_clock_interaction -file [file join $root reports clock_interaction.rpt]
report_bus_skew -file [file join $root reports bus_skew.rpt]
report_cdc -details -file [file join $root reports cdc_details.rpt]
report_methodology -file [file join $root reports methodology.rpt]
check_timing -verbose -file [file join $root reports check_timing.rpt]
report_compile_order -used_in synthesis -file [file join $root reports compile_order.rpt]
puts NETWORK_FINAL_IMPLEMENTATION_AUDIT_PASS
close_project
exit
