
`timescale 1 ns / 1 ps

	module oneburstwrite_v1_0_M00_AXI #
	(
		// Users to add parameters here
		parameter COLNUM=1024,
		parameter ROWNUM=512,
		parameter [4:0] IDLE = 5'b00001,
		parameter [4:0] ROWCONTROL   = 5'b00010,
		parameter [4:0] COLCONTROL   = 5'b00100,
		parameter [4:0] ADDRCOUNT    = 5'b01000,
		parameter [4:0] WRITECONTROL   = 5'b10000,
		parameter [31:0]      ADDRBASE= 32'h500000,
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
		//input  wire  [10:0] fft_last_cnt,
		output wire [4:0] my_status,
		output wire frame_end,
		output wire rd_1dfifo_en,
		input  wire [63:0] rd_1dfifo_data, 
		output wire debug_write_start,
		
		//input wire read_finish,
		//input wire [31:0] fifo_data_count,
		output wire [2:0] block_flag,
		output wire [31:0] addr_cnt_debug,
		input wire        	fifo_valid,
		input	wire		fft_last,
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


	// function called clogb2 that returns an integer which has the
	//value of the ceiling of the log base 2

	  // function called clogb2 that returns an integer which has the 
	  // value of the ceiling of the log base 2.                      
	  function integer clogb2 (input integer bit_depth);              
	  begin                                                           
	    for(clogb2=0; bit_depth>0; clogb2=clogb2+1)                   
	      bit_depth = bit_depth >> 1;                                 
	    end                                                           
	  endfunction                                                     

	// C_TRANSACTIONS_NUM is the width of the index counter for 
	// number of write or read transaction.
	 localparam integer C_TRANSACTIONS_NUM = clogb2(C_M_AXI_BURST_LEN-1);

	// Burst length for transactions, in C_M_AXI_DATA_WIDTHs.
	// Non-2^n lengths will eventually cause bursts across 4K address boundaries.
	 localparam integer C_MASTER_LENGTH	= 12;
	// total number of burst transfers is master length divided by burst length and burst size
	 localparam integer C_NO_BURSTS_REQ = C_MASTER_LENGTH-clogb2((C_M_AXI_BURST_LEN*C_M_AXI_DATA_WIDTH/8)-1);
	// Example State machine to initialize counter, initialize write transactions, 
	// initialize read transactions and comparison of read data with the 
	// written data words.
    localparam CLEAR_NUM =20; //前后要清除的行数

	 reg [1:0] mst_exec_state;

	// AXI4LITE signals
	//AXI4 internal temp signals
	reg [C_M_AXI_ADDR_WIDTH-1 : 0] 	axi_awaddr;
	reg  	axi_awvalid;
	reg [C_M_AXI_DATA_WIDTH-1 : 0] 	axi_wdata;
	reg  	axi_wlast;
	reg  	axi_wvalid;
	reg  	axi_bready;
	reg [C_M_AXI_ADDR_WIDTH-1 : 0] 	axi_araddr;
	reg  	axi_arvalid;
	reg  	axi_rready;
	//write beat count in a burst
	reg [C_TRANSACTIONS_NUM : 0] 	write_index;
	//read beat count in a burst
	reg [C_TRANSACTIONS_NUM : 0] 	read_index;
	//size of C_M_AXI_BURST_LEN length burst in bytes
	wire [C_TRANSACTIONS_NUM+2 : 0] 	burst_size_bytes;
	//The burst counters are used to track the number of burst transfers of C_M_AXI_BURST_LEN burst length needed to transfer 2^C_MASTER_LENGTH bytes of data.
	reg [C_NO_BURSTS_REQ : 0] 	write_burst_counter;
	reg [C_NO_BURSTS_REQ : 0] 	read_burst_counter;
	reg  	start_single_burst_write;
	reg  	start_single_burst_read;
	reg  	writes_done;
	reg  	reads_done;
	reg  	error_reg;
	reg  	compare_done;
	reg  	read_mismatch;
	reg  	burst_write_active;
	reg  	burst_read_active;
	reg [C_M_AXI_DATA_WIDTH-1 : 0] 	expected_rdata;
	//Interface response error flags
	wire  	write_resp_error;
	wire  	read_resp_error;
	wire  	wnext;
	wire  	rnext;
	reg  	init_txn_ff;
	reg  	init_txn_ff2;
	reg  	init_txn_edge;
	wire  	init_txn_pulse;
	
/*--------------------------my reg-------------------------*/	
	
reg		row_control_end;
reg		col_control_end;
reg		addr_count_end;
reg     row_enough;
reg		col_enough;
reg     both_enough;
reg [15:0]  row_cnt=0;
reg [15:0]  col_cnt=0;

reg 	row_control_en=0;
reg		row_control_en_d;

reg 	col_control_en=0;
reg		col_control_en_d;

reg 	write_control_en=0;

reg [31:0]  addr_cnt=0;
reg [15:0] 	wlast_cnt=0;

reg [15:0]   row_enough_cnt;
reg         write_start=0;
reg         write_start_d;

reg  [2:0]       addr_block_flag=1;
reg [15:0]  addr_count_row_256=256;
reg [15:0]  addr_count_row=0;
assign    block_flag=addr_block_flag;
assign    addr_cnt_debug=addr_cnt;

reg [15:0] 	fft_last_cnt=0;

reg [15:0]  fft_one_control_cnt=0;
reg         fft_last_d;
reg [4:0] stage_machine_reg;
/*--------------------------my reg-------------------------*/	

	// I/O Connections assignments

	//I/O Connections. Write Address (AW)
	assign M_AXI_AWID	= 'b0;
	//The AXI address is a concatenation of the target base address + active offset range
	assign M_AXI_AWADDR	= C_M_TARGET_SLAVE_BASE_ADDR + axi_awaddr;
	//Burst LENgth is number of transaction beats, minus 1
	assign M_AXI_AWLEN	= C_M_AXI_BURST_LEN - 1;
	//Size should be C_M_AXI_DATA_WIDTH, in 2^SIZE bytes, otherwise narrow bursts are used
	assign M_AXI_AWSIZE	= clogb2((C_M_AXI_DATA_WIDTH/8)-1);
	//INCR burst type is usually used, except for keyhole bursts
	assign M_AXI_AWBURST	= 2'b01;
	assign M_AXI_AWLOCK	= 1'b0;
	//Update value to 4'b0011 if coherent accesses to be used via the Zynq ACP port. Not Allocated, Modifiable, not Bufferable. Not Bufferable since this example is meant to test memory, not intermediate cache. 
	assign M_AXI_AWCACHE	= 4'b0010;
	assign M_AXI_AWPROT	= 3'h0;
	assign M_AXI_AWQOS	= 4'h0;
	assign M_AXI_AWUSER	= 'b1;
	assign M_AXI_AWVALID	= axi_awvalid;
	//Write Data(W)
	assign M_AXI_WDATA	= ((col_cnt> 0 && col_cnt<  CLEAR_NUM+1) || (col_cnt> 'd1004 && col_cnt <'d1025) )?'d0:rd_1dfifo_data;  //除去前后20行
	//assign M_AXI_WDATA	= rd_1dfifo_data;  //除去前后20行
	//assign M_AXI_WDATA	= axi_wdata;
	//All bursts are complete and aligned in this example
	assign M_AXI_WSTRB	= {(C_M_AXI_DATA_WIDTH/8){1'b1}};
	assign M_AXI_WLAST	= axi_wlast;
	assign M_AXI_WUSER	= 'b0;
	assign M_AXI_WVALID	= axi_wvalid;
	//Write Response (B)
	assign M_AXI_BREADY	= axi_bready;
	//Read Address (AR)
	assign M_AXI_ARID	= 'b0;
	assign M_AXI_ARADDR	= C_M_TARGET_SLAVE_BASE_ADDR + axi_araddr;
	//Burst LENgth is number of transaction beats, minus 1
	assign M_AXI_ARLEN	= C_M_AXI_BURST_LEN - 1;
	//Size should be C_M_AXI_DATA_WIDTH, in 2^n bytes, otherwise narrow bursts are used
	assign M_AXI_ARSIZE	= clogb2((C_M_AXI_DATA_WIDTH/8)-1);
	//INCR burst type is usually used, except for keyhole bursts
	assign M_AXI_ARBURST	= 2'b01;
	assign M_AXI_ARLOCK	= 1'b0;
	//Update value to 4'b0011 if coherent accesses to be used via the Zynq ACP port. Not Allocated, Modifiable, not Bufferable. Not Bufferable since this example is meant to test memory, not intermediate cache. 
	assign M_AXI_ARCACHE	= 4'b0010;
	assign M_AXI_ARPROT	= 3'h0;
	assign M_AXI_ARQOS	= 4'h0;
	assign M_AXI_ARUSER	= 'b1;
	assign M_AXI_ARVALID	= axi_arvalid;
	//Read and Read Response (R)
	assign M_AXI_RREADY	= axi_rready;
	//Example design I/O
	assign TXN_DONE	= compare_done;
	//Burst size in bytes
	assign burst_size_bytes	= C_M_AXI_BURST_LEN * C_M_AXI_DATA_WIDTH/8;
	assign init_txn_pulse	= (!init_txn_ff2) && init_txn_ff;


	//Generate a pulse to initiate AXI transaction.
	always @(posedge M_AXI_ACLK)										      
	  begin                                                                        
	    // Initiates AXI transaction delay    
	    if (M_AXI_ARESETN == 0 )                                                   
	      begin                                                                    
	        init_txn_ff <= 1'b0;                                                   
	        init_txn_ff2 <= 1'b0;                                                   
	      end                                                                               
	    else                                                                       
	      begin  
	        init_txn_ff <= INIT_AXI_TXN;
	        init_txn_ff2 <= init_txn_ff;                                                                 
	      end                                                                      
	  end     






/*--------------------------my wire-------------------------*/	
wire row_control_flag;
wire col_control_flag;
wire write_start_flag;
assign frame_end=both_enough;
assign my_status=stage_machine_reg;
/*--------------------------my wire-------------------------*/	


/*--------------------------start control-------------------------*/
/*
always @(posedge M_AXI_ACLK) begin
	write_start_d<=write_start;
end


always @(posedge M_AXI_ACLK) begin       
     if(both_enough==1)
        write_start<=0;
     else if(fifo_data_count>3000)       // if fifo data>3000 means has enough data for one burst write
		write_start<=1;
end

assign write_start_flag=(write_start)&&(!write_start_d);
assign debug_write_start=write_start_flag;
*/
/*--------------------------start control-------------------------*/



/*--------------------------row control-------------------------*/	
always @(posedge M_AXI_ACLK) begin
	if( M_AXI_ARESETN==0 || fft_last_cnt==512)
		fft_last_cnt<=0;
	else if(fft_last==1)
		fft_last_cnt<=fft_last_cnt+1;
end

always@(posedge M_AXI_ACLK)
    fft_last_d<=fft_last;

always @(posedge M_AXI_ACLK) begin    //??????????1024??????fft_last==1??????????????   ?????fft_last==1?????fifo??????д??1024????
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		row_control_en<=0;
	else if(row_control_end==1)
		row_control_en<=0;
	else if((stage_machine_reg==ROWCONTROL && fft_last_cnt==1 && fft_one_control_cnt<1) || (stage_machine_reg==ROWCONTROL && (fft_last_cnt>1) && (fft_last_d==1)))
		row_control_en<=1;
end

always@(posedge M_AXI_ACLK)begin
    if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
        fft_one_control_cnt<=0;
    else if(row_control_flag==1)
        fft_one_control_cnt<=fft_one_control_cnt+1;
end

always @(posedge M_AXI_ACLK) begin
	row_control_en_d<=row_control_en;
end

assign row_control_flag=(!row_control_en_d)&&(row_control_en); //??  ???row control???????????????

always@(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		row_cnt<=0;
	else if(row_control_flag==1 )
		row_cnt<=row_cnt+1;
	else
		row_cnt<=row_cnt;
end

always@(posedge M_AXI_ACLK)begin
    if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
        addr_count_row_256<=256;
    else if(row_control_flag==1 && row_cnt<256)
        addr_count_row_256<=addr_count_row_256+1;
end

always@(posedge M_AXI_ACLK)begin
    if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
        addr_count_row<=0;
    else if(row_control_flag==1 && row_cnt>=256)
        addr_count_row<=addr_count_row+1;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		row_control_end<=0;
	else if(row_control_flag==1)
		row_control_end<=1;
	else
		row_control_end<=0;
end

/*--------------------------row control-------------------------*/	


/*--------------------------col control-------------------------*/	
always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		col_control_en<=0;
	else if(col_control_end==1)
		col_control_en<=0;
	else if(stage_machine_reg==COLCONTROL)
		col_control_en<=1;
	
end

always @(posedge M_AXI_ACLK) begin
	col_control_en_d<=col_control_en;
end

assign col_control_flag=(!col_control_en_d)&&(col_control_en); //??  ???col control???????????????

always@(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE || row_enough==1)  //   ??1024??????????????
		col_cnt<=0;
	else if(col_control_flag==1)
		col_cnt<=col_cnt+1;
	else
		col_cnt<=col_cnt;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		col_control_end<=0;
	else if(col_control_flag==1)
		col_control_end<=1;
	else
		col_control_end<=0;
end

/*--------------------------col control-------------------------*/	



/*--------------------------addr count-------------------------*/	
always @(posedge M_AXI_ACLK) begin        //圆周位移
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		addr_cnt<=0;
	else if(col_control_end==1 && addr_block_flag==1 && col_cnt<=ROWNUM)
        addr_cnt<=((row_cnt-1)+((col_cnt+ROWNUM-1)<<(clogb2(ROWNUM-1))))<<3;
    else if(col_control_end==1 && addr_block_flag==1 && col_cnt>ROWNUM)
        addr_cnt<=((row_cnt-1)+((col_cnt-ROWNUM-1)<<(clogb2(ROWNUM-1))))<<3;
    else if(col_control_end==1 && addr_block_flag==2 && col_cnt<=ROWNUM)
        addr_cnt<=(ADDRBASE)+(((row_cnt-1)+((col_cnt+ROWNUM-1)<<(clogb2(ROWNUM-1))))<<3);
    else if(col_control_end==1 && addr_block_flag==2 && col_cnt>ROWNUM)
        addr_cnt<=(ADDRBASE)+(((row_cnt-1)+((col_cnt-ROWNUM-1)<<(clogb2(ROWNUM-1))))<<3);
end

always @(posedge M_AXI_ACLK) begin
	addr_count_end<=col_control_end;
end
/*--------------------------addr count-------------------------*/	


/*--------------------------write control-------------------------*/	
always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		write_control_en<=0;
	else if(stage_machine_reg==ROWCONTROL || stage_machine_reg==COLCONTROL) 
		write_control_en<=0;         //?????????????????????
	else if(axi_awvalid==1)    // ?????????????????,???????awvalid?????1??
		write_control_en<=1;
end



always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		axi_awvalid<=0;
	else if(axi_awvalid==1 && M_AXI_AWREADY==1)
		axi_awvalid<=0;
	else if(stage_machine_reg==WRITECONTROL && axi_awvalid==0 && axi_wvalid==0 && write_control_en==0)
		axi_awvalid<=1;
end	


always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_wvalid<=0;
	else if(axi_wvalid==1 && M_AXI_WREADY==1)
		axi_wvalid<=0;
	else if(axi_awvalid==1 && M_AXI_AWREADY==1 )
		axi_wvalid<=1;
end


always @(*) begin
	if(axi_wvalid==1 && M_AXI_WREADY==1 )
		axi_wlast<=1;
	else
		axi_wlast<=0;
end

always @(posedge M_AXI_ACLK ) begin
	if(M_AXI_ARESETN==0)
		axi_bready<=0;
	else
		axi_bready<=1;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_awaddr<=0;
//	else if(axi_awvalid==1 && M_AXI_AWREADY==1 )
//		axi_awaddr<=axi_awaddr+8;   // ????  1????
	else 
		axi_awaddr<=addr_cnt;
end

/*
always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_wdata<=0;
	else if(axi_wvalid==1 && M_AXI_WREADY==1 && axi_wdata==COLNUM-1)   
		axi_wdata<=0;
	else if(axi_wvalid==1 && M_AXI_WREADY==1)
		axi_wdata<=axi_wdata+1;
end
*/

assign rd_1dfifo_en=(axi_wvalid==1 )&&( M_AXI_WREADY==1)&&(fifo_valid==1);


always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		wlast_cnt<=0;
	else if(wlast_cnt==COLNUM)
		wlast_cnt<=0;          
	else if(axi_wlast==1)
		wlast_cnt<=wlast_cnt+1;
end

always @(posedge M_AXI_ACLK) begin
	if(wlast_cnt<COLNUM-1 && axi_wlast==1)
		col_enough<=1;
	else
		col_enough<=0;
end

always @(posedge M_AXI_ACLK) begin
	if(axi_wlast==1 && wlast_cnt==COLNUM-1 && row_enough_cnt<ROWNUM-1)
		row_enough<=1;
	else
		row_enough<=0;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		row_enough_cnt<=0;
	else if(axi_wlast==1 && wlast_cnt==COLNUM-1)
		row_enough_cnt<=row_enough_cnt+1;
end

always @(posedge M_AXI_ACLK) begin
	if(row_enough_cnt==ROWNUM-1 && axi_wlast==1 && wlast_cnt==COLNUM-1)
		both_enough<=1;
	else
		both_enough<=0;
end

always @(posedge M_AXI_ACLK) begin
	if(row_enough_cnt==ROWNUM-1 && axi_wlast==1 && wlast_cnt==COLNUM-1 && addr_block_flag==2)
		addr_block_flag<=1;    //flag between 0 to 1
	else if(row_enough_cnt==ROWNUM-1 && axi_wlast==1 && wlast_cnt==COLNUM-1 && addr_block_flag==1)
	   addr_block_flag<=2;
end

/*--------------------------write control-------------------------*/	


/*--------------------------stage machine-------------------------*/	
always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0)
		stage_machine_reg<=IDLE;
	else
		case(stage_machine_reg)
			IDLE:
				if(fft_last==1'b1)// only suit for continue trigger 
				//if(init_txn_pulse==1'b1 )
					stage_machine_reg<=ROWCONTROL;
				else
					stage_machine_reg<=IDLE;
			ROWCONTROL:
				if(row_control_end==1'b1)
					stage_machine_reg<=COLCONTROL;
				else
					stage_machine_reg<=ROWCONTROL;
			COLCONTROL:
				if(col_control_end==1'b1)
					stage_machine_reg<=ADDRCOUNT;
				else
					stage_machine_reg<=COLCONTROL;
			ADDRCOUNT:
				if(addr_count_end==1'b1)
					stage_machine_reg<=WRITECONTROL;
				else
					stage_machine_reg<=ADDRCOUNT;
			WRITECONTROL:
				if(both_enough==1'b1)
					stage_machine_reg<=IDLE;
				else if(row_enough==1'b1)
					stage_machine_reg<=ROWCONTROL;
				else if(col_enough==1'b1)
					stage_machine_reg<=COLCONTROL;
				else
					stage_machine_reg<=WRITECONTROL;
			default:
				stage_machine_reg<=IDLE;
		endcase

end

/*--------------------------stage machine-------------------------*/


	endmodule
