`timescale 1ns / 1ps

// Convert the DCA1000 UDP payload exposed by udp_rx into RX0 complex samples.
//
// A DCA1000 data packet starts with a 10-byte (five 16-bit word) packet
// header. The following ADC data is interleaved as eight 16-bit values per
// sample time: RX0 I, RX1 I, RX2 I, RX3 I, RX0 Q, RX1 Q, RX2 Q, RX3 Q.
// This block emits one 32-bit word {RX0_Q, RX0_I} for every group of eight.
//
// Unlike the legacy implementation, TVALID/TDATA/TLAST are held stable while
// TREADY is low. Non-data UDP ports cannot create a transfer with stale ADC
// data. The asynchronous FIFO immediately downstream provides the elasticity
// required by the UDP source, which itself cannot be backpressured.
module native2axis #(
    parameter integer DATA_PORT = 4098,
    parameter integer C_M_AXIS_TDATA_WIDTH = 128,
    parameter integer C_M_START_COUNT = 32
) (
    input  wire [15:0] rec_data,
    input  wire        rec_en,
    input  wire        rec_pkt_done,
    input  wire [15:0] dst_port,

    input  wire M_AXIS_ACLK,
    input  wire M_AXIS_ARESETN,
    output wire M_AXIS_TVALID,
    output wire [C_M_AXIS_TDATA_WIDTH-1:0] M_AXIS_TDATA,
    output wire [(C_M_AXIS_TDATA_WIDTH/8)-1:0] M_AXIS_TSTRB,
    output wire M_AXIS_TLAST,
    input  wire M_AXIS_TREADY,
    output reg [3:0] capture_fault
);

    localparam integer HEADER_HALFWORDS = 5;
    localparam integer CHIRP_SAMPLES = 1024;

    reg [2:0] header_halfword_count;
    reg [2:0] lane_halfword_count;
    reg [9:0] chirp_sample_count;
    reg [15:0] rx0_i;

    reg        out_valid;
    reg        out_last;
    reg [31:0] out_data;
    reg [31:0] packet_sequence;
    reg [31:0] previous_sequence;
    reg [47:0] packet_offset;
    reg [47:0] next_offset;
    reg [15:0] payload_bytes;
    reg seen_packet;

    wire output_slot_available;
    wire data_halfword;

    assign output_slot_available = !out_valid || M_AXIS_TREADY;
    assign data_halfword = rec_en && (dst_port == DATA_PORT);

    assign M_AXIS_TVALID = out_valid;
    assign M_AXIS_TDATA = out_data;
    assign M_AXIS_TLAST = out_last;
    assign M_AXIS_TSTRB = {(C_M_AXIS_TDATA_WIDTH/8){1'b1}};

    always @(posedge M_AXIS_ACLK) begin
        if (!M_AXIS_ARESETN) begin
            header_halfword_count <= 3'd0;
            lane_halfword_count <= 3'd0;
            chirp_sample_count <= 10'd0;
            rx0_i <= 16'd0;
            out_valid <= 1'b0;
            out_last <= 1'b0;
            out_data <= 32'd0;
            packet_sequence <= 0;
            previous_sequence <= 0;
            packet_offset <= 0;
            next_offset <= 0;
            payload_bytes <= 0;
            seen_packet <= 0;
            capture_fault <= 0;
        end else begin
            // Retire the current AXI word only on a handshake.
            if (out_valid && M_AXIS_TREADY) begin
                out_valid <= 1'b0;
                out_last <= 1'b0;
            end

            if (data_halfword) begin
                if (header_halfword_count < HEADER_HALFWORDS) begin
                    header_halfword_count <= header_halfword_count + 1'b1;
                    case (header_halfword_count)
                        0: begin
                            packet_sequence[15:0] <= rec_data;
                            payload_bytes <= 0;
                        end
                        1: begin
                            packet_sequence[31:16] <= rec_data;
                            if (seen_packet &&
                                {rec_data, packet_sequence[15:0]} != previous_sequence + 1)
                                capture_fault[0] <= 1; // sequence gap/reorder
                            previous_sequence <= {rec_data, packet_sequence[15:0]};
                        end
                        2: packet_offset[15:0] <= rec_data;
                        3: packet_offset[31:16] <= rec_data;
                        4: begin
                            packet_offset[47:32] <= rec_data;
                            if (seen_packet && {rec_data, packet_offset[31:0]} != next_offset)
                                capture_fault[1] <= 1; // ADC byte offset gap
                            if (!seen_packet && {rec_data, packet_offset[31:0]} != 0)
                                capture_fault[3] <= 1; // missing beginning
                            seen_packet <= 1;
                            // Byte offset, not UDP boundary, identifies the
                            // ADC lane. This also handles a split sample group.
                            lane_halfword_count <= packet_offset[3:1];
                        end
                        default: ;
                    endcase
                end else begin
                    payload_bytes <= payload_bytes + 2;
                    case (lane_halfword_count)
                        3'd0: rx0_i <= rec_data;
                        3'd4: begin
                            // The UDP source cannot be stopped. Under normal
                            // operation the downstream async FIFO is ready.
                            // If it stalls, retain the pending word instead of
                            // violating the AXI hold rule.
                            if (output_slot_available) begin
                                out_data <= {rec_data, rx0_i};
                                out_valid <= 1'b1;
                                out_last <=
                                    (chirp_sample_count == CHIRP_SAMPLES-1);
                                if (chirp_sample_count == CHIRP_SAMPLES-1)
                                    chirp_sample_count <= 10'd0;
                                else
                                    chirp_sample_count <=
                                        chirp_sample_count + 1'b1;
                            end else begin
                                capture_fault[2] <= 1; // UDP cannot backpressure
                            end
                        end
                        default: ;
                    endcase

                    if (lane_halfword_count == 3'd7)
                        lane_halfword_count <= 3'd0;
                    else
                        lane_halfword_count <= lane_halfword_count + 1'b1;
                end

                // Offset is the number of ADC bytes before this packet.
                if (rec_pkt_done) begin
                    header_halfword_count <= 3'd0;
                    next_offset <= packet_offset + payload_bytes + 2;
                end
            end else if (rec_pkt_done) begin
                header_halfword_count <= 3'd0;
            end
        end
    end

    // Retained for packaged-IP interface compatibility.
    wire unused_start_count = (C_M_START_COUNT == 0);

endmodule
