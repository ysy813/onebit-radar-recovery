`timescale 1ns/1ps
// One elastic delivery slot per consumer. Each accepted source word is
// delivered exactly once to each ENABLED downstream FIFO.
// A full branch eventually backpressures the source; it never silently drops
// or duplicates data. The UDP parser reports overflow if finite buffering is
// exhausted. No finite FIFO can hide an indefinitely stopped consumer.
module axis_selectable_fork #(
    parameter integer DATA_WIDTH=32
)(
    input wire clk, input wire rst_n,
    // bit0=image, bit1=storage. Set only before radar input starts; reset PL
    // between tests. Disabled branches cannot hold up an enabled branch.
    input wire [1:0] branch_enable,
    input wire [DATA_WIDTH-1:0] s_axis_tdata,
    input wire s_axis_tvalid, output wire s_axis_tready,
    output wire [DATA_WIDTH-1:0] m00_axis_tdata,
    output wire m00_axis_tvalid, input wire m00_axis_tready,
    output wire [DATA_WIDTH-1:0] m01_axis_tdata,
    output wire m01_axis_tvalid, input wire m01_axis_tready
);
    reg [DATA_WIDTH-1:0] held_data;
    reg pending_image, pending_store;
    assign s_axis_tready=rst_n && (|branch_enable) &&
        (!branch_enable[0] || !pending_image || m00_axis_tready) &&
        (!branch_enable[1] || !pending_store || m01_axis_tready);
    assign m00_axis_tdata=held_data;
    assign m01_axis_tdata=held_data;
    assign m00_axis_tvalid=rst_n && branch_enable[0] && pending_image;
    assign m01_axis_tvalid=rst_n && branch_enable[1] && pending_store;
    always @(posedge clk) begin
        if (!rst_n) begin
            held_data<=0; pending_image<=0; pending_store<=0;
        end else if (s_axis_tready) begin
            pending_image<=s_axis_tvalid && branch_enable[0];
            pending_store<=s_axis_tvalid && branch_enable[1];
            if (s_axis_tvalid) held_data<=s_axis_tdata;
        end else begin
            if (m00_axis_tready) pending_image<=0;
            if (m01_axis_tready) pending_store<=0;
        end
    end
endmodule
