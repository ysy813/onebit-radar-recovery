// UltraScale+ OSERDESE3 CLK/CLKDIV share one MMCM source. Use a normal
// BUFGCE for the full-rate path and BUFGCE_DIV for the divide-by-two path.
module hdmi_serdes_clocks(
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 raw_clock CLK", X_INTERFACE_PARAMETER="FREQ_HZ 371250000" *)
    input wire raw_clock,
    (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 reset_n RST", X_INTERFACE_PARAMETER="POLARITY ACTIVE_LOW" *)
    input wire reset_n,
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 clock_5x CLK", X_INTERFACE_PARAMETER="FREQ_HZ 371250000" *)
    output wire clock_5x,
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 clock_2_5x CLK", X_INTERFACE_PARAMETER="FREQ_HZ 185625000" *)
    output wire clock_2_5x
);
    BUFGCE #(.CE_TYPE("SYNC")) serial_buffer (
        .I(raw_clock),.CE(1'b1),.O(clock_5x));
    BUFGCE_DIV #(.BUFGCE_DIVIDE(2)) divided_buffer (
        .I(raw_clock),.CE(1'b1),.CLR(~reset_n),.O(clock_2_5x));
endmodule
