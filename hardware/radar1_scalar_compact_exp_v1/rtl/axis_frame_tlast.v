`timescale 1ns / 1ps

// Generates one AXI-Stream TLAST pulse every FRAME_WORDS accepted beats.
// TLAST remains asserted with the final beat during downstream backpressure.
module axis_frame_tlast #(
    parameter integer FRAME_WORDS = 524288,
    parameter integer COUNT_WIDTH = 19
) (
    input  wire clk,
    input  wire rst_n,
    input  wire s_axis_tvalid,
    input  wire s_axis_tready,
    output wire m_axis_tlast
);

    reg [COUNT_WIDTH-1:0] frame_word_count;
    wire                  accept;

    assign accept       = s_axis_tvalid && s_axis_tready;
    assign m_axis_tlast = (frame_word_count == FRAME_WORDS - 1);

    always @(posedge clk) begin
        if (!rst_n) begin
            frame_word_count <= {COUNT_WIDTH{1'b0}};
        end else if (accept) begin
            if (frame_word_count == FRAME_WORDS - 1)
                frame_word_count <= {COUNT_WIDTH{1'b0}};
            else
                frame_word_count <= frame_word_count + 1'b1;
        end
    end

endmodule
