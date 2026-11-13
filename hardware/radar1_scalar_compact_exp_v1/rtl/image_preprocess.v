`timescale 1ns / 1ps

// Startup-selectable imaging input. Storage splits off before this block.
// mode_request is latched with the first accepted word. Later changes are
// reported and cannot mix RAW and one-bit samples in one acquisition.
module image_preprocess #(
    parameter integer QUANT_AMPLITUDE = 64
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        mode_request,
    output wire        mode_active,
    output wire        mode_unsupported,
    input  wire [31:0] s_axis_tdata,
    input  wire        s_axis_tvalid,
    output wire        s_axis_tready,
    output wire [31:0] m_axis_tdata,
    output wire        m_axis_tvalid,
    input  wire        m_axis_tready
);
    localparam [15:0] POSITIVE = QUANT_AMPLITUDE;
    localparam [15:0] NEGATIVE = -QUANT_AMPLITUDE;
    reg [31:0] held_data;
    reg held_valid;
    reg mode_latched;
    reg mode_locked;

    wire selected_mode = mode_locked ? mode_latched : mode_request;
    wire [15:0] quant_i = s_axis_tdata[15] ? NEGATIVE : POSITIVE;
    wire [15:0] quant_q = s_axis_tdata[31] ? NEGATIVE : POSITIVE;
    wire [31:0] selected_data = selected_mode ? {quant_q, quant_i} : s_axis_tdata;

    assign s_axis_tready = rst_n && (!held_valid || m_axis_tready);
    assign m_axis_tdata = held_data;
    assign m_axis_tvalid = rst_n && held_valid;
    assign mode_active = mode_locked && mode_latched;
    assign mode_unsupported = mode_locked && (mode_request != mode_latched);

    always @(posedge clk) begin
        if (!rst_n) begin
            held_data <= 32'd0;
            held_valid <= 1'b0;
            mode_latched <= 1'b0;
            mode_locked <= 1'b0;
        end else if (s_axis_tready) begin
            held_valid <= s_axis_tvalid;
            if (s_axis_tvalid) begin
                held_data <= selected_data;
                if (!mode_locked) begin
                    mode_latched <= mode_request;
                    mode_locked <= 1'b1;
                end
            end
        end
    end
endmodule
