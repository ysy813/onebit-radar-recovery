
`timescale 1 ns / 1 ps

	module interp_ip_v1_0_M00_AXI #
	(
		// Users to add parameters here
        parameter           FRAME_NUM   = 1422140,  //843*1687-1
        parameter [31:0]    AR_ADDR_MAX = 11377120,  //(843*1687-1)*8
		parameter           COLNUM      = 843,
		parameter           ROWNUM      = 1687,
        parameter           S_COLNUM    = 157,
        parameter           S_ROWNUM    = 1024,
		parameter [5:0]     IDLE        = 6'b000001,
		parameter [5:0]     AR_READ     = 6'b000010,
		parameter [5:0]     ID_COUNT    = 6'b000100,
		parameter [5:0]     DATA_FIND   = 6'b001000,
        parameter [5:0]     NUM_ADD     = 6'b010000,
        parameter [5:0]     DOUT_WRITE  = 6'b100000,
		parameter [5:0]     W_ADDR_COUNT= 6'b100001,
        parameter [5:0]     Debug       = 6'b111111,
		parameter [31:0]    AR_ADDRBASE = 32'h3000000,
        parameter [31:0]    SM_ADDRBASE = 32'h4000000,
        parameter [31:0]    DO_ADDRBASE = 32'h5000000,
        parameter [31:0]    DO_ADDRBASE1= 32'h6000000,
       //parameter xid = 5,
        //parameter yid = 10,
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
		input   wire        fft2_done,
		output wire capture_start,
        //input   wire [15:0] xid,
		//input   wire [15:0] yid,
        output  wire [5:0]  stage_debug,
        output wire frame_end1,
        output wire frame_flag,
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
	
	assign M_AXI_WDATA	= axi_wdata;
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

/*--------------------------my reg-------------------------*/	
reg [5:0]   stage_machine_reg   =IDLE;	
reg [5:0]   stage_machine_reg_d,stage_machine_reg_d2;
reg         AR_READ_done        =0;
reg [63:0]  AR_data             =0;
wire         ID_COUNT_done;
reg         DATA_FIND_done      =0;
reg         DOUT_WRITE_done     =0;
reg         NUM_ADD_done        =0;
reg [31:0]  frame_num_count     =0;



reg [31:0]  AR_addr_cnt         =0;
reg         axi_rlast             ;
reg [31:0]  AR_stage_cnt        =0;


reg         ID_COUNT_start      =0;
reg [4:0]   ID_COUNT_debug      =0;

reg [7:0]   DATA_FIND_cnt       =0;
reg [63:0]  DATA_FIND_out       =0;

reg [31:0]  DOUT_WRITE_addr     =0;
reg [31:0]  DOUT_stage_cnt      =0;
reg [31:0]  wlast_cnt           =0;
reg [63:0]  r_rdata;
reg         r_axi_ready,r_axi_rvalid;
reg         frame_end           =0;
reg         frame_end_d;
wire        frame_end_p;
reg arvalid_d1 =0;
reg arvalid_d2 =0;
reg [63:0] frame_cnt;
reg cnt_ccen = 0;
reg [4:0] frame_end_cnt=0;
reg frame_flag_r=0;
/*--------------------------my reg-------------------------*/	
assign frame_end1 = frame_end;
always @(posedge M_AXI_ACLK)begin
  if(M_AXI_ARESETN==0)
  frame_cnt <= 0;
  else if(frame_end == 1)
  frame_cnt <= 0;
  else if(cnt_ccen == 1)
  frame_cnt <= frame_cnt + 1;
end


always @(posedge M_AXI_ACLK)begin
  if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
    frame_end_cnt <= 0;
  else if(fft2_done == 1 && cnt_ccen==1) //在整个插值过程中，来一次frame end 就加1次数
    frame_end_cnt <= frame_end_cnt+1;
  else
    frame_end_cnt<=frame_end_cnt;
end


always @(posedge M_AXI_ACLK)begin
if(M_AXI_ARESETN == 0)
  cnt_ccen <= 0;
else  if(frame_end == 1)
  cnt_ccen <= 0;
  else if(stage_machine_reg==AR_READ && stage_machine_reg_d==IDLE)
  cnt_ccen <= 1;
end

/*--------------------------my wire-------------------------*/	
//wire [35:0] xid_out;
wire [31:0]  DATA_FIND_addr;
// Guard the final linear byte offset; preserve legacy column carry.
wire power_offset_valid = (DATA_FIND_addr < 32'h00400000) && (DATA_FIND_addr[2:0] == 3'b000);
wire [15:0] xid;
wire [15:0] yid;
wire addr_done;
assign stage_debug=stage_machine_reg;
/*--------------------------my wire-------------------------*/	
CCID_count u_ccid_float(
    .clk(M_AXI_ACLK),
    .id_pulse(ID_COUNT_start),
    .AQ_data (AR_data[63:32]),
    .xid(xid),
    .id_done (ID_COUNT_done),
    .AR_data(AR_data[31:0]),    //AR数据与AQ数据以及合并在一起了
    .yid(yid), 
    .DATA_FIND_addr (DATA_FIND_addr),
    .addr_done (addr_done)

);



/*--------------------------AR read control-------------------------*/	
always @(posedge M_AXI_ACLK) begin
    {stage_machine_reg_d2,stage_machine_reg_d}<={stage_machine_reg_d,stage_machine_reg};     
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		AR_stage_cnt<=0;
	else if(stage_machine_reg==AR_READ && stage_machine_reg_d!=AR_READ)   //当状态跳转到AR_READ的时候 
		AR_stage_cnt<=AR_stage_cnt+1;
	else 
	    AR_stage_cnt<=AR_stage_cnt;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		AR_addr_cnt<=0;
	else if(stage_machine_reg==NUM_ADD && stage_machine_reg_d2!=NUM_ADD && AR_stage_cnt==FRAME_NUM+1) //当状态最后第一次跳转到AR_READ的时候（有可能不需要）
		AR_addr_cnt<=0;
	else if(stage_machine_reg==AR_READ && stage_machine_reg_d!=AR_READ && AR_stage_cnt==0)   //当状态第一次跳转到AR_READ的时候 
		AR_addr_cnt<=0;
    else if(stage_machine_reg==NUM_ADD && stage_machine_reg_d!=NUM_ADD )   //当状态跳转到NUM_ADD的时候 
        AR_addr_cnt<=AR_addr_cnt+8;
    else
        AR_addr_cnt<=AR_addr_cnt;
end	

always @(posedge M_AXI_ACLK) begin  //注意AR还是AQ还是SMALL读出来的数都要用这个
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		arvalid_d1<=0;
	else if(arvalid_d1==1 && M_AXI_ARREADY==1)
		arvalid_d1<=0;                              //为了优化时序，采用2级延迟
	else if( arvalid_d1==0 && axi_rready==0 && stage_machine_reg_d==AR_READ && stage_machine_reg_d2!=AR_READ )   //当状态跳转到AR_READ的时候开始读 
		arvalid_d1<=1; 
    else if( arvalid_d1==0 && axi_rready==0 && stage_machine_reg_d==DATA_FIND && DATA_FIND_cnt==3  )   //当状态跳转到DATA FIND并且计数到3 
        arvalid_d1<=1;
    else
        arvalid_d1<=arvalid_d1;        
end	

always @(posedge M_AXI_ACLK) begin
        arvalid_d2 <= arvalid_d1;
        axi_arvalid <= arvalid_d2;
end

always @(*) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_araddr<=0;
	else if(stage_machine_reg==AR_READ)  //如果在AR状态里就用AR的地址
		axi_araddr<=AR_ADDRBASE+AR_addr_cnt;
    else if(stage_machine_reg==DATA_FIND)
        axi_araddr<=SM_ADDRBASE+DATA_FIND_addr; 
    else 
        axi_araddr<=axi_araddr;
end

always @(posedge M_AXI_ACLK) begin
    if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
        axi_rready<=0;
    else if(axi_rready==1 && M_AXI_RVALID==1)
        axi_rready<=0;
    else if(axi_arvalid==1 && M_AXI_ARREADY==1)
        axi_rready<=1;
   else
        axi_rready<=axi_rready;
end

always @(posedge M_AXI_ACLK) begin
    if(axi_rready==1 && M_AXI_RVALID==1)
        axi_rlast<=1;
    else
        axi_rlast<=0;
end

always @(posedge M_AXI_ACLK ) begin
	if(M_AXI_ARESETN==0)
		axi_bready<=0;
	else
		axi_bready<=1;
end

always@(posedge M_AXI_ACLK)begin
    r_rdata<=M_AXI_RDATA;
    r_axi_ready<=axi_rready;
    r_axi_rvalid<=M_AXI_RVALID;
end



/*always @(*) begin
    if(axi_rready==1 && M_AXI_RVALID==1 && stage_machine_reg==AR_READ)   //在AR_READ状态中，读出来的数赋值给AR_data
        AR_data=M_AXI_RDATA;
      else 
      AR_data=AR_data;
end
*/

always @(*) begin
    if(axi_rready==1 && M_AXI_RVALID==1 && r_axi_rvalid==0 && stage_machine_reg_d==AR_READ)   //在AR_READ状态中，读出来的数赋值给AR_data 在上升沿获取
       AR_data=r_rdata;                      //这里是经过好多次时序调试出来的结果
      else 
      AR_data=AR_data;
end

always @* begin
    if(stage_machine_reg==AR_READ && axi_rlast==1)
        AR_READ_done=1;
    else 
        AR_READ_done=0;
end

/*--------------------------AR read control-------------------------*/	



/*--------------------------ID Count control-------------------------*/

always @(posedge M_AXI_ACLK) begin   
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		ID_COUNT_start<=0;
    else if(stage_machine_reg==ID_COUNT && stage_machine_reg_d!=ID_COUNT )  
        ID_COUNT_start<=1;
    else
        ID_COUNT_start<=0;
end	
/*--------------------------ID Count control-------------------------*/


/*--------------------------Data Find control-------------------------*/

always @(posedge M_AXI_ACLK) begin   
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		DATA_FIND_cnt<=0;
    else if(DATA_FIND_done==1 || stage_machine_reg!=DATA_FIND)
        DATA_FIND_cnt<=0;
    else if(stage_machine_reg==DATA_FIND)  
        DATA_FIND_cnt<=DATA_FIND_cnt+1;
    else 
        DATA_FIND_cnt<=DATA_FIND_cnt;
end	

/*mult_gen mult_inst (
  .CLK(M_AXI_ACLK),  // input wire CLK
  .A(yid),      // input wire [15 : 0] A
  .P(xid_out)      // output wire [35 : 0] P
);*/

//assign   DATA_FIND_addr=(xid+xid_out[31:0])<<3;      

always @(posedge M_AXI_ACLK) begin
    if(axi_rready==1 && M_AXI_RVALID==1 && stage_machine_reg==DATA_FIND)   
        DATA_FIND_out<=M_AXI_RDATA;
    else
        DATA_FIND_out<=DATA_FIND_out;
end

always @* begin
    if(stage_machine_reg==DATA_FIND && axi_rlast==1)
        DATA_FIND_done=1;
    else 
        DATA_FIND_done=0;
end

/*--------------------------Data Find control-------------------------*/

/*-----------------------------Write ADDR COUNT-----------------------------*/

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		DOUT_stage_cnt<=0;
	else if(stage_machine_reg==W_ADDR_COUNT && stage_machine_reg_d!=W_ADDR_COUNT)   //当状态跳转到W_ADDR_COUNT的时候 
		DOUT_stage_cnt<=DOUT_stage_cnt+1;
    else 
        DOUT_stage_cnt<=DOUT_stage_cnt;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
    DOUT_WRITE_addr<=0;
	else if(stage_machine_reg==W_ADDR_COUNT && stage_machine_reg_d!=W_ADDR_COUNT && DOUT_stage_cnt==0)   //当状态第一次跳转到W_ADDR_COUNT的时候 
		DOUT_WRITE_addr<=0;
    else if(stage_machine_reg==W_ADDR_COUNT && stage_machine_reg_d!=W_ADDR_COUNT)   //当状态跳转到W_ADDR_COUNT的时候 
        DOUT_WRITE_addr<=DOUT_WRITE_addr+8;
    else 
        DOUT_WRITE_addr<=DOUT_WRITE_addr;
        end	
/*-----------------------------Write ADDR COUNT-----------------------------*/


/*-----------------------------DOUT Write-----------------------------*/
always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0 || stage_machine_reg==IDLE)
		axi_awvalid<=0;
	else if(axi_awvalid==1 && M_AXI_AWREADY==1)
		axi_awvalid<=0;
	else if( axi_awvalid==0 && axi_wvalid==0 && stage_machine_reg_d==DOUT_WRITE && stage_machine_reg_d2!=DOUT_WRITE)
		axi_awvalid<=1;
    else
        axi_awvalid<=axi_awvalid;
end	

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_wvalid<=0;
	else if(axi_wvalid==1 && M_AXI_WREADY==1)
		axi_wvalid<=0;
	else if(axi_awvalid==1 && M_AXI_AWREADY==1 )
		axi_wvalid<=1;
    else 
        axi_wvalid<=axi_wvalid;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_wdata<=0;
    else if(stage_machine_reg==DOUT_WRITE && stage_machine_reg_d2==DATA_FIND) //从DATA_FIND来的，那就写入找出的数
        axi_wdata<=DATA_FIND_out; 
    else
        axi_wdata<=axi_wdata;  
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
		axi_awaddr<=0;
	else if(frame_flag==0)
		axi_awaddr<= DO_ADDRBASE+DOUT_WRITE_addr;    //根据不同的帧标志写入到不同的地方
	else if(frame_flag==1)
	   axi_awaddr<= DO_ADDRBASE1+DOUT_WRITE_addr;
	else
	   axi_awaddr<=axi_awaddr;
end


always @(*) begin
	if(axi_wvalid==1 && M_AXI_WREADY==1 )
		axi_wlast<=1;
	else
		axi_wlast<=0;
end

always @(posedge M_AXI_ACLK) begin
	if(axi_wlast==1 && stage_machine_reg==DOUT_WRITE)
		DOUT_WRITE_done<=1;
	else
		DOUT_WRITE_done<=0;
end

always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0  || stage_machine_reg==IDLE)
        wlast_cnt<=0;
    else if(axi_wlast==1 || (stage_machine_reg==NUM_ADD&& stage_machine_reg_d==W_ADDR_COUNT))  //没写数的也算上
		wlast_cnt<=wlast_cnt+1;
	else
	   wlast_cnt<=wlast_cnt;
end

/*-----------------------------DOUT Write-----------------------------*/

/*-----------------------------NUM ADD-----------------------------*/
assign capture_start = frame_end;
always @(posedge M_AXI_ACLK) begin
    if(wlast_cnt==FRAME_NUM+1 )   //等在NUM_ADD阶段，发现写满1帧的数据
		frame_end<=1;
    else 
        frame_end<=0;
end

always@(posedge M_AXI_ACLK)
    frame_end_d<=frame_end;

assign frame_end_p=(frame_end)&&(!frame_end_d);   //获取frame_end上升沿

always@(posedge M_AXI_ACLK)
    if(frame_end_p==1)
        frame_flag_r<=~frame_flag_r;
    else
        frame_flag_r<=frame_flag_r;    
        
assign frame_flag=frame_flag_r;        
/*-----------------------------NUM ADD-----------------------------*/



/*--------------------------stage machine-------------------------*/	
always @(posedge M_AXI_ACLK) begin
	if(M_AXI_ARESETN==0)begin
		stage_machine_reg<=IDLE;
    end
	else
		case(stage_machine_reg)
			IDLE:
				if(fft2_done==1'b1)    //当一帧二维FFT完成后，便开始启动插值
					stage_machine_reg<=AR_READ;
				else
					stage_machine_reg<=IDLE;
			
            AR_READ:
				if(AR_READ_done==1 && AR_data[31:0]!=0 )      //当读出的AR数据不为0的时候 才需要计算
					stage_machine_reg<=ID_COUNT;
                else if(AR_READ_done==1 && AR_data[31:0]==0)   //当读出的AR数据为0的时候 都不需要赋值
                    stage_machine_reg<=W_ADDR_COUNT;
                else
                    stage_machine_reg<=AR_READ;

            ID_COUNT:                               //计算xid yid
                if(addr_done==1)
                    stage_machine_reg<=power_offset_valid ? DATA_FIND : W_ADDR_COUNT;
                else
                    stage_machine_reg<=ID_COUNT;
            
         	DATA_FIND:                          // 在small矩阵中，根据xid yid找到对应的值
                if(DATA_FIND_done==1)
                    stage_machine_reg<=W_ADDR_COUNT;
                else
                    stage_machine_reg<=DATA_FIND;
            
			W_ADDR_COUNT:
				if(stage_machine_reg_d==AR_READ || stage_machine_reg_d==ID_COUNT) //如果是从AR_READ这个状态过来的
					stage_machine_reg<=NUM_ADD;
				else 
					stage_machine_reg<=DOUT_WRITE;   //否则就需要写入数据
					
            DOUT_WRITE:                       //将data_out写入到PS端口中
                if(DOUT_WRITE_done==1)
                    stage_machine_reg<=NUM_ADD;
                else
                    stage_machine_reg<=DOUT_WRITE;
            
            NUM_ADD:
                if(frame_end==1) //如果自加完毕并且计数完成1帧 那么可以返回IDLE
                    stage_machine_reg<=IDLE;
                else                 //如果没有写完1帧，那就返回AR READ
                    stage_machine_reg<=AR_READ;
                
			default:
				stage_machine_reg<=IDLE;
		endcase

end
//wire [299:0] probe0;
/*assign probe0 = {
       ID_COUNT_start,
       xid,
       yid,
       frame_end_cnt,
       fft2_done,
       frame_end,
       stage_machine_reg,
		AR_addr_cnt,
       // DATA_FIND_addr,
        axi_rready,
        M_AXI_RVALID,
        axi_wvalid,
        M_AXI_WREADY,
       // DOUT_WRITE_addr,
       // axi_awvalid,
        M_AXI_AWREADY,
        r_axi_ready,
        r_axi_rvalid,
       // r_rdata,
       ID_COUNT_done,
      DATA_FIND_addr,
      addr_done,
      frame_cnt,
      axi_awaddr,
      frame_flag,
      cnt_ccen
      
      // DATA_FIND_done
};*/
/*--------------------------stage machine-------------------------*/
/*调用xid模块*/
/*ila_0 your_instance_name (
	.clk(M_AXI_ACLK), // input wire clk


	.probe0(probe0) // input wire [127:0] probe0
);*/

/************/

	endmodule

