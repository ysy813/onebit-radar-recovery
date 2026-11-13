set root [file dirname [file dirname [file normalize [info script]]]]
create_project sim_frame [file join $root sim frame_project] -part xczu4ev-sfvc784-1-i -force
add_files [list [file join $root rtl network_frame_control.v] [file join $root rtl network_cdc.v]]
add_files -fileset sim_1 [file join $root sim tb_frame.sv]
set_property top tb_frame [get_filesets sim_1]
set_property xsim.simulate.runtime all [get_filesets sim_1]
launch_simulation
close_sim
close_project
exit
