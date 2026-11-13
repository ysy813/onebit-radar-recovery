`timescale 1ns / 1ps
// Sticky error bits only change from zero to one, independently. No
// multi-bit binary counter crosses the clock boundary.
module capture_fault_sync(input wire clk, input wire rst_n,
    input wire [3:0] fault_async, output wire [3:0] fault_sync);
    (* ASYNC_REG = "TRUE" *) reg [3:0] ff1, ff2;
    always @(posedge clk) begin
        if (!rst_n) begin ff1 <= 0; ff2 <= 0; end
        else begin ff1 <= fault_async; ff2 <= ff1; end
    end
    assign fault_sync = ff2;
endmodule
