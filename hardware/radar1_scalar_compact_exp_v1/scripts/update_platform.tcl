set root [file dirname [file dirname [file normalize [info script]]]]
setws [file join $root vitis]
platform active scalar
platform config -updatehw [file join $root pkg scalar_network.xsa]
domain active standalone_domain
platform generate
puts SCALAR_FINAL_PLATFORM_PASS
exit
