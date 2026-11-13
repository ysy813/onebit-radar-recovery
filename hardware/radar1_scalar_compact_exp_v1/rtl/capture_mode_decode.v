`timescale 1ns / 1ps

// AXI GPIO channel 2: bit0 imaging, bit1 storage, bit2 one-bit imaging.
module capture_mode_decode (
    input wire [2:0] control,
    output wire [1:0] branch_enable,
    output wire mode_request
);
    assign branch_enable = control[1:0];
    assign mode_request = control[2];
endmodule
