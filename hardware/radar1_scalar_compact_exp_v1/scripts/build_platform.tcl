set root [file dirname [file dirname [file normalize [info script]]]]
set workspace [file join $root vitis]
setws $workspace
platform create -name scalar -hw [file join $root pkg scalar_network.xsa] -proc psu_cortexa53_0 -os standalone -out $workspace
platform active scalar
domain active standalone_domain
bsp setlib -name xilffs -ver 4.7
bsp config read_only false
bsp config use_mkfs false
bsp write
platform generate
puts SCALAR_FINAL_PLATFORM_PASS
exit
