
`timescale 1 ns / 1 ps

	module display_v1_0_M00_AXI #
	(
		// Users to add parameters here
        parameter FRAME1_BASEADDR=32'h1000000,
		// User parameters ends
		// Do not modify the parameters beyond this line

		// Base address of targeted slave
		parameter  C_M_TARGET_SLAVE_BASE_ADDR	= 32'h40000000,
		// Burst Length. Supports 1, 2, 4, 8, 16, 32, 64, 128, 256 burst lengths
		parameter integer C_M_AXI_BURST_LEN	= 16,
		// Thread ID Width
		parameter integer C_M_AXI_ID_WIDTH	= 1,
		// Width of Address Bus
		parameter integer C_M_AXI_ADDR_WIDTH	= 32,
		// Width of Data Bus
		parameter integer C_M_AXI_DATA_WIDTH	= 32,
		// Width of User Write Address Bus
		parameter integer C_M_AXI_AWUSER_WIDTH	= 0,
		// Width of User Read Address Bus
		parameter integer C_M_AXI_ARUSER_WIDTH	= 0,
		// Width of User Write Data Bus
		parameter integer C_M_AXI_WUSER_WIDTH	= 0,
		// Width of User Read Data Bus
		parameter integer C_M_AXI_RUSER_WIDTH	= 0,
		// Width of User Response Bus
		parameter integer C_M_AXI_BUSER_WIDTH	= 0
	)
	(
		// Users to add ports here
        input   wire        rd_clk                  ,
        input   wire        capture_start           ,
        input   wire        rd_en                   ,
        input   wire        frame_flag              ,
        output	wire [63:0]	rd_data_out             ,
        output  wire        hdmi_start              ,
        
        output  wire [13:0] fifo_data_count_out     ,
        output  wire        read_cycle_debug        ,
        output  wire  [1:0]      stage_debug             ,
		// User ports ends
		// Do not modify the ports beyond this line

		// Initiate AXI transactions
		input wire  INIT_AXI_TXN,
		// Asserts when transaction is complete
		output wire  TXN_DONE,
		// Asserts when ERROR is detected
		output reg  ERROR,
		// Global Clock Signal.
		input wire  M_AXI_ACLK,
		// Global Reset Singal. This Signal is Active Low
		input wire  M_AXI_ARESETN,
		// Master Interface Write Address ID
		output wire [C_M_AXI_ID_WIDTH-1 : 0] M_AXI_AWID,
		// Master Interface Write Address
		output wire [C_M_AXI_ADDR_WIDTH-1 : 0] M_AXI_AWADDR,
		// Burst length. The burst length gives the exact number of transfers in a burst
		output wire [7 : 0] M_AXI_AWLEN,
		// Burst size. This signal indicates the size of each transfer in the burst
		output wire [2 : 0] M_AXI_AWSIZE,
		// Burst type. The burst type and the size information, 
    // determine how the address for each transfer within the burst is calculated.
		output wire [1 : 0] M_AXI_AWBURST,
		// Lock type. Provides additional information about the
    // atomic characteristics of the transfer.
		output wire  M_AXI_AWLOCK,
		// Memory type. This signal indicates how transactions
    // are required to progress through a system.
		output wire [3 : 0] M_AXI_AWCACHE,
		// Protection type. This signal indicates the privilege
    // and security level of the transaction, and whether
    // the transaction is a data access or an instruction access.
		output wire [2 : 0] M_AXI_AWPROT,
		// Quality of Service, QoS identifier sent for each write transaction.
		output wire [3 : 0] M_AXI_AWQOS,
		// Optional User-defined signal in the write address channel.
		output wire [C_M_AXI_AWUSER_WIDTH-1 : 0] M_AXI_AWUSER,
		// Write address valid. This signal indicates that
    // the channel is signaling valid write address and control information.
		output wire  M_AXI_AWVALID,
		// Write address ready. This signal indicates that
    // the slave is ready to accept an address and associated control signals
		input wire  M_AXI_AWREADY,
		// Master Interface Write Data.
		output wire [C_M_AXI_DATA_WIDTH-1 : 0] M_AXI_WDATA,
		// Write strobes. This signal indicates which byte
    // lanes hold valid data. There is one write strobe
    // bit for each eight bits of the write data bus.
		output wire [C_M_AXI_DATA_WIDTH/8-1 : 0] M_AXI_WSTRB,
		// Write last. This signal indicates the last transfer in a write burst.
		output wire  M_AXI_WLAST,
		// Optional User-defined signal in the write data channel.
		output wire [C_M_AXI_WUSER_WIDTH-1 : 0] M_AXI_WUSER,
		// Write valid. This signal indicates that valid write
    // data and strobes are available
		output wire  M_AXI_WVALID,
		// Write ready. This signal indicates that the slave
    // can accept the write data.
		input wire  M_AXI_WREADY,
		// Master Interface Write Response.
		input wire [C_M_AXI_ID_WIDTH-1 : 0] M_AXI_BID,
		// Write response. This signal indicates the status of the write transaction.
		input wire [1 : 0] M_AXI_BRESP,
		// Optional User-defined signal in the write response channel
		input wire [C_M_AXI_BUSER_WIDTH-1 : 0] M_AXI_BUSER,
		// Write response valid. This signal indicates that the
    // channel is signaling a valid write response.
		input wire  M_AXI_BVALID,
		// Response ready. This signal indicates that the master
    // can accept a write response.
		output wire  M_AXI_BREADY,
		// Master Interface Read Address.
		output wire [C_M_AXI_ID_WIDTH-1 : 0] M_AXI_ARID,
		// Read address. This signal indicates the initial
    // address of a read burst transaction.
		output wire [C_M_AXI_ADDR_WIDTH-1 : 0] M_AXI_ARADDR,
		// Burst length. The burst length gives the exact number of transfers in a burst
		output wire [7 : 0] M_AXI_ARLEN,
		// Burst size. This signal indicates the size of each transfer in the burst
		output wire [2 : 0] M_AXI_ARSIZE,
		// Burst type. The burst type and the size information, 
    // determine how the address for each transfer within the burst is calculated.
		output wire [1 : 0] M_AXI_ARBURST,
		// Lock type. Provides additional information about the
    // atomic characteristics of the transfer.
		output wire  M_AXI_ARLOCK,
		// Memory type. This signal indicates how transactions
    // are required to progress through a system.
		output wire [3 : 0] M_AXI_ARCACHE,
		// Protection type. This signal indicates the privilege
    // and security level of the transaction, and whether
    // the transaction is a data access or an instruction access.
		output wire [2 : 0] M_AXI_ARPROT,
		// Quality of Service, QoS identifier sent for each read transaction
		output wire [3 : 0] M_AXI_ARQOS,
		// Optional User-defined signal in the read address channel.
		output wire [C_M_AXI_ARUSER_WIDTH-1 : 0] M_AXI_ARUSER,
		// Write address valid. This signal indicates that
    // the channel is signaling valid read address and control information
		output wire  M_AXI_ARVALID,
		// Read address ready. This signal indicates that
    // the slave is ready to accept an address and associated control signals
		input wire  M_AXI_ARREADY,
		// Read ID tag. This signal is the identification tag
    // for the read data group of signals generated by the slave.
		input wire [C_M_AXI_ID_WIDTH-1 : 0] M_AXI_RID,
		// Master Read Data
		input wire [C_M_AXI_DATA_WIDTH-1 : 0] M_AXI_RDATA,
		// Read response. This signal indicates the status of the read transfer
		input wire [1 : 0] M_AXI_RRESP,
		// Read last. This signal indicates the last transfer in a read burst
		input wire  M_AXI_RLAST,
		// Optional User-defined signal in the read address channel.
		input wire [C_M_AXI_RUSER_WIDTH-1 : 0] M_AXI_RUSER,
		// Read valid. This signal indicates that the channel
    // is signaling the required read data.
		input wire  M_AXI_RVALID,
		// Read ready. This signal indicates that the master can
    // accept the read data and response information.
		output wire  M_AXI_RREADY
	);


    // Standard 720p scanout of the complete legacy 1687 x 843 power image.
    // Read even source rows, retain even columns: 844 x 422 pixels.
    // Only this read path resamples; interpolation and the DDR image format stay intact.
    localparam integer SOURCE_WIDTH=1687, OUTPUT_HEIGHT=422;
    localparam [31:0] SOURCE_ROW_STEP=32'd26992; // 2 * 1687 * 8
    localparam [1:0] WAIT_IMAGE=0, ISSUE=1, RECEIVE=2;
    reg [1:0] state=WAIT_IMAGE;
    reg [31:0] address=0,row_base=0;
    reg [10:0] column=0;
    reg [8:0] row=0;
    reg arvalid=0;
    reg [8:0] burst_beats=0,beat=0;
    wire [9:0] page_words=10'd512-{1'b0,address[11:3]};
    wire [10:0] row_words=SOURCE_WIDTH-column;
    wire [9:0] page_limit=(page_words>256) ? 10'd256 : page_words;
    wire [8:0] next_beats=(row_words<page_limit) ? row_words[8:0] : page_limit[8:0];
    wire [31:0] next_frame_base=C_M_TARGET_SLAVE_BASE_ADDR+(frame_flag ? 32'd0 : FRAME1_BASEADDR);
    wire fifo_full,fifo_empty,wr_busy,rd_busy,overflow,underflow;
    wire [12:0] wr_count,rd_count;
    wire [63:0] fifo_data;
    wire pixel_reset;
    reg pixel_underflow=0;
    wire underflow_axi;
    wire keep_word=~column[0];
    wire accepted=M_AXI_RVALID && M_AXI_RREADY;
    wire fifo_write=accepted && keep_word;
    wire fifo_read=rd_en && !fifo_empty && !rd_busy && !pixel_reset;

    assign M_AXI_ARID=0;
    assign M_AXI_ARADDR=address;
    assign M_AXI_ARLEN=burst_beats-1'b1;
    assign M_AXI_ARSIZE=3'd3;
    assign M_AXI_ARBURST=2'b01;
    assign M_AXI_ARLOCK=0;
    assign M_AXI_ARCACHE=4'b0010;
    assign M_AXI_ARPROT=0;
    assign M_AXI_ARQOS=0;
    assign M_AXI_ARUSER=0;
    assign M_AXI_ARVALID=arvalid;
    assign M_AXI_RREADY=(state==RECEIVE) && !wr_busy && (!keep_word || !fifo_full);
    // This master only reads the existing display banks.
    assign M_AXI_AWID=0;
    assign M_AXI_AWADDR=0;
    assign M_AXI_AWLEN=0;
    assign M_AXI_AWSIZE=3'd3;
    assign M_AXI_AWBURST=2'b01;
    assign M_AXI_AWLOCK=0;
    assign M_AXI_AWCACHE=0;
    assign M_AXI_AWPROT=0;
    assign M_AXI_AWQOS=0;
    assign M_AXI_AWUSER=0;
    assign M_AXI_AWVALID=0;
    assign M_AXI_WDATA=0;
    assign M_AXI_WSTRB=0;
    assign M_AXI_WLAST=0;
    assign M_AXI_WUSER=0;
    assign M_AXI_WVALID=0;
    assign M_AXI_BREADY=1;
    assign TXN_DONE=0;
    assign fifo_data_count_out={1'b0,wr_count};
    assign read_cycle_debug=(state==RECEIVE);
    assign stage_debug=state;
    assign rd_data_out=(fifo_empty || rd_busy || pixel_reset) ? 64'd0 : fifo_data;

    always @(posedge M_AXI_ACLK) begin
        if(!M_AXI_ARESETN) begin
            state<=WAIT_IMAGE;address<=0;row_base<=0;column<=0;row<=0;
            arvalid<=0;burst_beats<=0;beat<=0;ERROR<=0;
        end else begin
            if(overflow || underflow_axi) ERROR<=1;
            case(state)
                WAIT_IMAGE: if(capture_start) begin
                    address<=next_frame_base;row_base<=next_frame_base;
                    column<=0;row<=0;state<=ISSUE;
                end
                ISSUE: begin
                    // Reserve an entire burst before issuing it. At most 128 words survive decimation.
                    if(!arvalid && !wr_busy && wr_count<3000) begin
                        burst_beats<=next_beats;arvalid<=1;
                    end
                    if(arvalid && M_AXI_ARREADY) begin
                        arvalid<=0;beat<=0;state<=RECEIVE;
                    end
                end
                RECEIVE: if(accepted) begin
                    if(M_AXI_RRESP!=0 || M_AXI_RLAST!=(beat==burst_beats-1'b1)) ERROR<=1;
                    column<=column+1'b1;
                    beat<=beat+1'b1;
                    if(beat==burst_beats-1'b1) begin
                        state<=ISSUE;
                        if(column==SOURCE_WIDTH-1) begin
                            column<=0;
                            if(row==OUTPUT_HEIGHT-1) begin
                                row<=0;row_base<=next_frame_base;address<=next_frame_base;
                            end else begin
                                row<=row+1'b1;
                                row_base<=row_base+SOURCE_ROW_STEP;
                                address<=row_base+SOURCE_ROW_STEP;
                            end
                        end else address<=address+{20'd0,burst_beats,3'd0};
                    end
                end
                default:state<=WAIT_IMAGE;
            endcase
        end
    end

    xpm_cdc_async_rst #(.DEST_SYNC_FF(4),.INIT_SYNC_FF(0),.RST_ACTIVE_HIGH(1))
        pixel_reset_sync(.src_arst(~M_AXI_ARESETN),.dest_clk(rd_clk),.dest_arst(pixel_reset));
    reg video_started=0;
    assign hdmi_start=video_started;
    always @(posedge rd_clk or posedge pixel_reset) begin
        if(pixel_reset) begin video_started<=0;pixel_underflow<=0;end
        else begin
            if(!rd_busy && rd_count>2000) video_started<=1;
            if(video_started && rd_en && fifo_empty) pixel_underflow<=1;
        end
    end
    xpm_cdc_single #(.DEST_SYNC_FF(4),.SRC_INPUT_REG(0))
        underflow_sync(.src_clk(rd_clk),.src_in(pixel_underflow),.dest_clk(M_AXI_ACLK),.dest_out(underflow_axi));
    xpm_fifo_async #(
        .FIFO_MEMORY_TYPE("block"),.FIFO_WRITE_DEPTH(4096),.WRITE_DATA_WIDTH(64),.READ_DATA_WIDTH(64),
        .READ_MODE("fwft"),.FIFO_READ_LATENCY(0),.CDC_SYNC_STAGES(2),.DOUT_RESET_VALUE("0"),
        .ECC_MODE("no_ecc"),.FULL_RESET_VALUE(0),.PROG_EMPTY_THRESH(10),.PROG_FULL_THRESH(4000),
        .RD_DATA_COUNT_WIDTH(13),.WR_DATA_COUNT_WIDTH(13),.RELATED_CLOCKS(0),.USE_ADV_FEATURES("0707"),
        .SIM_ASSERT_CHK(0),.WAKEUP_TIME(0)
    ) scanout_fifo (
        .rst(~M_AXI_ARESETN),.sleep(1'b0),.wr_clk(M_AXI_ACLK),.wr_en(fifo_write),.din(M_AXI_RDATA),
        .full(fifo_full),.overflow(overflow),.wr_rst_busy(wr_busy),.wr_data_count(wr_count),
        .prog_full(),.almost_full(),.wr_ack(),
        .rd_clk(rd_clk),.rd_en(fifo_read),.dout(fifo_data),.empty(fifo_empty),.underflow(underflow),
        .rd_rst_busy(rd_busy),.rd_data_count(rd_count),.prog_empty(),.almost_empty(),.data_valid(),
        .injectsbiterr(1'b0),.injectdbiterr(1'b0),.sbiterr(),.dbiterr()
    );
endmodule
