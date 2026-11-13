

module tx_ctrl #(
    parameter SHORT_PK_PORT = 16'd4096
    )
    (
    input                clk           ,     
    input                rst_n         ,     

    input                key           ,   


    output  reg  [2 :0]	 short_pk 	   ,  
    output  reg          tx_start_en     
    );

`ifndef SIMULATION
localparam CNT_BIT           = 30; 
`else
localparam CNT_BIT           = 3; 
`endif 

// states definition
//`ifndef SIMULATION
localparam  IDLE             = 5'b00001,    
            SEND             = 5'b00010,   
            WAIT_REC_EN      = 5'b00100,   
            WAIT_TIME        = 5'b01000,   
            END_SEND         = 5'b10000; 
localparam  STATE_WIDE       = 5       ;

parameter   WAIT_CNT         = 75000000;
//`else
//localparam  IDLE             = "IDLE"  ,    
//            SEND             = "SEND"  ,   
//            WAIT_REC_EN      = "WAIT_R",   
//            WAIT_TIME        = "WAIT_T",   
//            END_SEND         = "END"   ; 
//localparam  STATE_WIDE       = 48      ;
//`endif 
reg  [STATE_WIDE-1:0]  cur_state;
reg  [STATE_WIDE-1:0]  next_state; 

reg  key_d0;
reg  key_d1;
wire pos_key;
reg  [ 1: 0] reset_r;
reg  [CNT_BIT - 1: 0] delay_cnt;
wire reset;
reg  [4:0] mystate=IDLE;
assign pos_key = (~key_d1) & key_d0;    
assign reset = reset_r[1];
reg         send_end    =0      ;
reg         wait_end    =0      ;
reg [3:0]   wait_end_cnt=0      ;
reg         send_ctrl   =0      ;
reg         send_ctrl_d         ;
wire        send_flag           ;


always @(posedge clk ) begin
    reset_r[0] <= !rst_n;
    reset_r[1] <= reset_r[0];
end

always @(posedge clk) begin  
    if(reset)begin
        key_d0 <= 1'b0;
        key_d1 <= 1'b0;
    end
    else begin
        key_d0 <= key;
        key_d1 <= key_d0;
    end
end
/********************************/
/*     3-stage state machine    */
/********************************/
always @(posedge clk) begin
    if(reset)
        mystate<=IDLE;
    else
        case (mystate)
        IDLE:   if(pos_key==1)
                    mystate<=SEND;
                else
                    mystate<=IDLE;

        SEND:   if(send_end==1)
                    mystate<=WAIT_TIME;
                else
                    mystate<=SEND;
        
        WAIT_TIME:  if(wait_end==1 && wait_end_cnt==5)
                        mystate<=IDLE;
                    else if(wait_end==1)
                        mystate<=SEND;
                    else
                        mystate<=WAIT_TIME;
            default: mystate<=IDLE;
        endcase
end

always@(posedge clk)
    if(reset || mystate==IDLE)
        send_ctrl<=0;
    else if(mystate==SEND)
        send_ctrl<=1;
    else 
        send_ctrl<=0;

always@(posedge clk)
    send_ctrl_d<=send_ctrl;

assign send_flag=(send_ctrl)&&(!send_ctrl_d);

always @(posedge clk) begin
    if(reset)
        send_end<=0;
    else if(mystate==SEND)
        send_end<=1;
    
end

always @(posedge clk) begin
    if(reset || mystate==IDLE)
        tx_start_en<=0;
    else if(send_flag==1)
        tx_start_en<=1;
    else
        tx_start_en<=0;
end

always @(posedge clk) begin
    if(reset || mystate==IDLE)
        short_pk<=0;
    else if(send_flag==1)
        short_pk<=short_pk+1;
end

always @(posedge clk) begin
    if(reset || mystate==IDLE)
        delay_cnt<=0;
    else if(delay_cnt==WAIT_CNT-1)
        delay_cnt<=0;
    else if(mystate==WAIT_TIME)
        delay_cnt<=delay_cnt+1;
end

always @(posedge clk) begin
    if(reset || mystate==IDLE)
        wait_end<=0;
    else if(delay_cnt==WAIT_CNT-1)
        wait_end<=1;
    else
        wait_end<=0;
end

always @(posedge  clk) begin
    if(reset || mystate==IDLE)
        wait_end_cnt<=0;
    else if(wait_end==1)
        wait_end_cnt<=wait_end_cnt+1;
end


endmodule
