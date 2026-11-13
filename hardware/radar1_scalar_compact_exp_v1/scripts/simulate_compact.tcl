set root [file dirname [file dirname [file normalize [info script]]]]
create_project sim_compact [file join $root sim compact_project] -part xczu4ev-sfvc784-1-i -force
add_files [glob [file join $root hls project solution syn verilog *.v]]
foreach f [glob [file join $root hls project solution syn verilog *.dat]] {add_files -fileset sim_1 $f}
foreach name {tb_compact_mlp tb_compact_guard} {
    add_files -fileset sim_1 [file join $root sim ${name}.sv]
    add_files -fileset sim_1 [file join $root sim ${name}.hex]
}
set_property xsim.simulate.runtime all [get_filesets sim_1]
foreach name {tb_compact_mlp tb_compact_guard} {
    set_property top $name [get_filesets sim_1]
    launch_simulation
    close_sim
}
close_project
puts COMPACT_RTL_SIMULATIONS_DONE
exit
