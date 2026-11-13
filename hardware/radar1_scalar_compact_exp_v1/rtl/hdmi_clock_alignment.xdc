# OSERDESE3 requires CLK and CLKDIV insertion delays to track. These are
# related 5x / 2.5x outputs of the SAME MMCM; retain all setup/hold checks.
set hdmi_gearbox_nets [get_nets -of_objects [get_pins {design_1_i/hdmi_serdes_clocks_0/inst/serial_buffer/O design_1_i/hdmi_serdes_clocks_0/inst/divided_buffer/O}]]
# Check the two resolved nets in the final Tcl audit (XDC has limited Tcl).
set_property CLOCK_DELAY_GROUP HDMI_GEARBOX $hdmi_gearbox_nets
# All four serializer CLK/CLKDIV pairs are in X1Y3. Anchor both shared clock
# roots there rather than at the divided clock's logic-load centroid X0Y2.
# This changes real clock routing; it does not relax the OSERDES skew limit.
set_property USER_CLOCK_ROOT X1Y3 $hdmi_gearbox_nets
