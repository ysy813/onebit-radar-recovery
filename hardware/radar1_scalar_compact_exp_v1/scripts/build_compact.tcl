# Update the already integrated independent radar1 design. No hardware access.
set root [file dirname [file dirname [file normalize [info script]]]]
open_project [file join $root project imaging_storage.xpr]
set repos [glob -type d [file join $root ip_repo *]]
lappend repos [file join $root hls project solution impl ip]
set_property ip_repo_paths $repos [current_project]
set_property ip_output_repo [file join $root project imaging_storage.cache ip] [current_project]
update_ip_catalog -rebuild
open_bd_design [get_files design_1.bd]
upgrade_bd_cells [get_bd_cells scalar_gain_0]
# Module ports are unchanged; reset/generate below reuses the edited RTL source.
set_property CONFIG.Coe_File [file join $root FFTSHIFT.coe] [get_bd_cells blk_mem_gen_0]
validate_bd_design
save_bd_design
reset_target all [get_files design_1.bd]
generate_target all [get_files design_1.bd]
update_compile_order -fileset sources_1
reset_run network_synth
close_project
source [file join $root scripts build_hardware.tcl]
