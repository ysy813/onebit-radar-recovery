`timescale 1ns/1ps
// Original simultaneous-only fork, retained for reproducibility of the
// previous hw_package. Isolation build uses axis_selectable_fork instead.
module axis_buffered_fork #(
    parameter integer DATA_WIDTH=32
)(
    input wire clk, input wire rst_n,
    input wire [DATA_WIDTH-1:0] s_axis_tdata,
    input wire s_axis_tvalid, output wire s_axis_tready,
    output wire [DATA_WIDTH-1:0] m00_axis_tdata,
    output wire m00_axis_tvalid, input wire m00_axis_tready,
    output wire [DATA_WIDTH-1:0] m01_axis_tdata,
    output wire m01_axis_tvalid, input wire m01_axis_tready
);
    reg [DATA_WIDTH-1:0] held_data;
    reg pending_image, pending_store;
    assign s_axis_tready=rst_n && (!pending_image || m00_axis_tready) &&
                                      (!pending_store || m01_axis_tready);
    assign m00_axis_tdata=held_data;
    assign m01_axis_tdata=held_data;
    assign m00_axis_tvalid=rst_n && pending_image;
    assign m01_axis_tvalid=rst_n && pending_store;
    always @(posedge clk) begin
        if (!rst_n) begin
            held_data<=0; pending_image<=0; pending_store<=0;
        end else if (s_axis_tready) begin
            pending_image<=s_axis_tvalid;
            pending_store<=s_axis_tvalid;
            if (s_axis_tvalid) held_data<=s_axis_tdata;
        end else begin
            if (m00_axis_tready) pending_image<=0;
            if (m01_axis_tready) pending_store<=0;
        end
    end
endmodule
