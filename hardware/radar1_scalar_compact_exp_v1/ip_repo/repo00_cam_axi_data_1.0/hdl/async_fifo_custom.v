// Custom async FIFO - avoids Vivado 2022.1 XPM FIFO output pipeline bug
// Depth: 1024, Width: 32, FWFT read mode
// Zero XPM components: plain Verilog with tool-inferred RAM
module async_fifo_custom (
    input wire rst_n,           // active-low async reset
    input wire wr_clk,
    input wire wr_en,
    input wire [31:0] din,
    output wire full,
    output wire overflow,
    output wire [10:0] wr_data_count,
    input wire rd_clk,
    input wire rd_en,
    output reg [31:0] dout,
    output wire empty,
    output wire underflow,
    output wire [10:0] rd_data_count
);

    localparam ADDR_W = 10;  // 1024 depth
    localparam PTR_W = 11;   // 10 addr + 1 status bit

    // ---- Memory array (tool infers BRAM or LUTRAM) ----
    reg [31:0] mem [0:1023];
    reg [ADDR_W-1:0] wr_addr_r;
    reg [ADDR_W-1:0] rd_addr_r;

    // ---- Pointers (binary, MSB = direction) ----
    reg [PTR_W-1:0] wr_ptr;
    reg [PTR_W-1:0] rd_ptr;

    // ---- Gray code ----
    wire [PTR_W-1:0] wr_gray = wr_ptr ^ (wr_ptr >> 1);
    wire [PTR_W-1:0] rd_gray = rd_ptr ^ (rd_ptr >> 1);

    // ---- CDC synchronizers (2-flop each) ----
    reg [PTR_W-1:0] wr_g_sync1, wr_g_sync2;
    reg [PTR_W-1:0] rd_g_sync1, rd_g_sync2;

    // ---- Gray to binary ----
    function [PTR_W-1:0] g2b;
        input [PTR_W-1:0] g;
        integer i;
        begin
            g2b[PTR_W-1] = g[PTR_W-1];
            for (i = PTR_W-2; i >= 0; i = i-1)
                g2b[i] = g2b[i+1] ^ g[i];
        end
    endfunction

    wire [PTR_W-1:0] rd_p_sync = g2b(wr_g_sync2);
    wire [PTR_W-1:0] wr_p_sync = g2b(rd_g_sync2);

    // ---- Full/empty detection ----
    wire full_w  = (wr_ptr == {~rd_p_sync[PTR_W-1], rd_p_sync[PTR_W-2:0]});
    wire empty_w = (rd_ptr == wr_p_sync);

    assign full  = full_w;
    assign empty = (rd_fill_stage != 2);

    // ---- Data counts ----
    assign wr_data_count = wr_ptr - rd_p_sync;
    assign rd_data_count = wr_p_sync - rd_ptr;

    // ====================================================================
    // Write domain
    // ====================================================================
    reg overflow_r;
    assign overflow = overflow_r;

    always @(posedge wr_clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr    <= 0;
            wr_addr_r <= 0;
            overflow_r <= 0;
        end else begin
            overflow_r <= wr_en & full_w;
            if (wr_en && !full_w) begin
                wr_ptr    <= wr_ptr + 1;
                wr_addr_r <= wr_ptr[ADDR_W-1:0];
            end
        end
    end

    always @(posedge wr_clk) begin
        if (wr_en && !full_w)
            mem[wr_addr_r] <= din;
    end

    // ====================================================================
    // Read domain — FWFT (First-Word Fall-Through)
    // ====================================================================
    // Memory read with 1-cycle latency
    reg [31:0] mem_dout_r;
    always @(posedge rd_clk) begin
        mem_dout_r <= mem[rd_addr_r];
    end

    // FWFT pipeline:
    //   stage 0 = empty, stage 1 = pre-fetch in flight, stage 2 = dout valid
    reg [1:0] rd_fill_stage;
    reg underflow_r;
    assign underflow = underflow_r;

    always @(posedge rd_clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr        <= 0;
            rd_addr_r     <= 0;
            dout          <= 0;
            rd_fill_stage <= 0;
            underflow_r   <= 0;
        end else begin
            underflow_r <= rd_en & (rd_fill_stage != 2);

            case (rd_fill_stage)
            0: begin  // empty: start pre-fetch if data available
                if (rd_ptr != wr_p_sync) begin
                    rd_addr_r     <= rd_ptr[ADDR_W-1:0];
                    rd_ptr        <= rd_ptr + 1;
                    rd_fill_stage <= 1;
                end
            end
            1: begin  // pre-fetch in flight: data will be in mem_dout_r this cycle
                dout          <= mem_dout_r;
                rd_fill_stage <= 2;
                if (rd_ptr != wr_p_sync) begin
                    rd_addr_r <= rd_ptr[ADDR_W-1:0];
                    rd_ptr    <= rd_ptr + 1;
                end
            end
            2: begin  // normal: dout valid, advance on rd_en
                if (rd_en) begin
                    dout <= mem_dout_r;
                    if (rd_ptr != wr_p_sync) begin
                        rd_addr_r <= rd_ptr[ADDR_W-1:0];
                        rd_ptr    <= rd_ptr + 1;
                    end else begin
                        rd_fill_stage <= 0;
                    end
                end
            end
            endcase
        end
    end

    // ---- CDC sync for gray pointers ----
    always @(posedge rd_clk or negedge rst_n) begin
        if (!rst_n) {wr_g_sync2, wr_g_sync1} <= 0;
        else         {wr_g_sync2, wr_g_sync1} <= {wr_g_sync1, wr_gray};
    end

    always @(posedge wr_clk or negedge rst_n) begin
        if (!rst_n) {rd_g_sync2, rd_g_sync1} <= 0;
        else         {rd_g_sync2, rd_g_sync1} <= {rd_g_sync1, rd_gray};
    end

endmodule
