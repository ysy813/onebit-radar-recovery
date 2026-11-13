`timescale  1ns / 1ps
//****************************
//        simulate a PHY 
//****************************
module tb_eth_udp_loop;

// define mac addr and ip addr
localparam DATA_FILE = "C:/Users/Administrator/Desktop/python_eth_rx_tx/22_eth_udp_loop/01matlab/table_256x4.bin";
// localparam DATA_FILE = "../01matlab/table_256x4.bin";

localparam  BOARD_MAC   = 48'h00_11_22_33_44_55          ;     
localparam  BOARD_IP    = {8'd192,8'd168,8'd33,8'd30}    ;   
localparam  RADAR_MAC   = 48'h20_7b_d2_59_38_5a          ;    //48'hf4_8e_38_a8_07_90 or 48'h12_34_56_78_90_12         
localparam  RADAR_IP    = {8'd192,8'd168,8'd33,8'd180}   ;  
localparam  UDP_PERIOD = 8                               ;
localparam  SYS_PERIOD = 20                              ;
localparam  T_HOLD = 0.5                                 ;                        
localparam  PREAMBEL_LEN = 8                             ;
localparam  ETH_HEAD_LEN = 14                            ;
localparam  IP_HEAD_LEN  = 20                            ;
localparam  UDP_HEAD_LEN = 8                             ;
localparam  CRC_LEN      = 4                             ;
localparam  UDP_PACK_NUM   = 12                          ;
localparam  ARP_LEN = 28                                 ;
                           
reg    phy_tx_clk                           = 0 ; //PHY  tx clk
reg    phy_tx_clk_delay                     = 0 ;
reg    phy_tx_ctl                           = 0 ; 
reg    [3:0]  phy_tx_data                   = 0 ;

// wire   phy_rx_clk                           = 0 ; //PHY  tx clk
// wire   phy_rx_ctl                           = 0 ; 
// wire   [3:0]  phy_rx_data                   = 0 ;
// eth_udp_loop Inputs
// reg   sys_clk                               = 0          ; 
reg   sys_rst_n                             = 1          ; 
reg   key                                   = 0          ;
wire   eth_rxc                                           ;   //PHY core delay tx clk
wire   eth_rx_ctl                                        ;   //wire logic can't be initiated
wire   [3:0]  eth_rxd                                    ;
// eth_udp_loop Outputs         
wire  eth_txc                                            ;
wire  eth_tx_ctl                                         ;
wire  [3:0]  eth_txd                                     ;
// wire  eth_rst_n                                          ;
              
reg  [15:0 ] cnt     = 0                                 ;
              
reg [0:UDP_PACK_NUM-1] [0:732] [15: 0] one_data          ;
reg [0:7] [15:0] arp_data    = '{1,2,3,4,5,6,7,8}        ;                    
reg [0:7] [15:0] short_data  = '{1,2,3,4,5,6,7,8}        ;   
         
integer       fd1, err, read_code                        ;
reg  [320:0]  str                                        ;
// connect ports
assign  eth_rxc    = phy_tx_clk_delay;
assign  eth_rx_ctl = phy_tx_ctl;
assign  eth_rxd    = phy_tx_data;

// generate clock
// always #(SYS_PERIOD/2)  sys_clk          <= ~sys_clk     ;
always #(UDP_PERIOD/2)  phy_tx_clk       <= ~phy_tx_clk  ;  //not block assigment : <= must be used 
always #(UDP_PERIOD/4)  phy_tx_clk_delay <= phy_tx_clk   ;  //not block assigment : <= must be used 

initial begin
    #(SYS_PERIOD * 50) sys_rst_n  <=  0;
    #(SYS_PERIOD * 3)   sys_rst_n  <=  1;
end

/*------------------------------------*/
/*         prepare for data           */
/*------------------------------------*/
initial begin
    fd1 = $fopen(DATA_FILE, "rb");  
    err = $ferror(fd1, str);
    $display("Error number is: %h.", err );  //0
    $display("Error info is: %s.", str );    //0
    if( !err)begin
        read_code = $fread(one_data, fd1);      //return the readed num of bytes
        $display("Read code is :%d.", read_code);
    end
    $fclose(fd1);
end

//behavior
initial begin
    #(SYS_PERIOD * 51);
    wait(sys_rst_n == 1);
    #(SYS_PERIOD *2);

    @(posedge phy_tx_clk) #T_HOLD key <= 1;
    @(posedge phy_tx_clk) #T_HOLD key <= 0;
    #(UDP_PERIOD * 100);                 //wait for respond
    
    @(posedge phy_tx_clk) #T_HOLD;
    drive_frame(arp_data, 1024, 4096, 8, 0);
    #(UDP_PERIOD * 80);                 //wait for respond

    for (integer i = 1;i<=6 ; i=i+1) begin
        @(posedge phy_tx_clk) #T_HOLD;
        drive_frame(short_data, 1024, 4096, 8, 1);
        #(UDP_PERIOD * 100);                 //wait for respond
    end
    for (integer i = 0;i<=UDP_PACK_NUM-1 ; i=i+1) begin
        @(posedge phy_tx_clk) #T_HOLD;
        drive_frame(one_data[i], 1024, 4098, 1466/2, 1);
        #(UDP_PERIOD*30);                               //wait some time to send the next udp pack
    end
    #3000;
    $stop;
end

/* Send a udp data
--data    : the data to send  */
task automatic drive_byte;
input [7: 0] data;
// input        last;
begin
    phy_tx_data <= data[3:0];
    phy_tx_ctl <= 1;         //valid
    @(negedge phy_tx_clk) #T_HOLD;
    phy_tx_data <= data[7:4];
    phy_tx_ctl <= 1;         //no err
    @(posedge phy_tx_clk) #T_HOLD;
    phy_tx_ctl <= 0;
end
endtask //automatic

/* Send a udp frame
--data      : the frame to send
--src_port  : the port of the source device
--des_port  : the port of the destinate device
--len       : the nums of the half-word data   
--send_type : 1-udp, 0-arp*/
task automatic drive_frame;
input [0:732] [15:0] data;
input [15:0] src_port;
input [15:0] des_port;
input integer len;
input integer send_type;

reg [15: 0] ip_num = 28 + len * 2;
reg [15: 0] udp_num = 8 + len * 2; 
begin
    /*----------------  send preamble   ----------------*/
    for (integer i = 1;i<= PREAMBEL_LEN-1; i = i+1) begin
        drive_byte(8'h55);
    end
    drive_byte(8'hd5);
    /*----------------  send eth head   ----------------*/
    for (integer i = 1;i<= ETH_HEAD_LEN; i = i+1) begin
        case (i)
            // 1~6: destinate MAC
            1:  if(send_type ==1 )  drive_byte(BOARD_MAC[47:40]);
                else  drive_byte(8'hff);    
            2:  if(send_type ==1 )  drive_byte(BOARD_MAC[39:32]);
                else  drive_byte(8'hff);
            3:  if(send_type ==1 )  drive_byte(BOARD_MAC[31:24]);
                else  drive_byte(8'hff);
            4:  if(send_type ==1 )  drive_byte(BOARD_MAC[23:16]);
                else  drive_byte(8'hff);
            5:  if(send_type ==1 )  drive_byte(BOARD_MAC[15:8 ]);
                else  drive_byte(8'hff);            
            6:  if(send_type ==1 )  drive_byte(BOARD_MAC[7 :0 ]);
                else  drive_byte(8'hff);
            //  7~12: source MAC
            7:  drive_byte(RADAR_MAC[47:40]);
            8:  drive_byte(RADAR_MAC[39:32]);
            9:  drive_byte(RADAR_MAC[31:24]);
            10: drive_byte(RADAR_MAC[23:16]);
            11: drive_byte(RADAR_MAC[15:8 ]);
            12: drive_byte(RADAR_MAC[7 :0 ]);
            //  13 ~ 14 eth type:0x0800--IPv4,,0x0806--arp
            13: drive_byte(8'h08);
            14: if(send_type ==1 ) drive_byte(8'h00);
                else drive_byte(8'h06);
            default: ;
        endcase
    end
    if(send_type == 1)begin
        /*----------------  IP head   ----------------*/
        for (integer i = 1; i <= IP_HEAD_LEN; i = i + 1 ) begin
            case (i)
                1 : drive_byte(8'h45);              //ipv4 and 5 words
                2 : drive_byte(8'h00);
                3 : drive_byte(ip_num[15:8]);       
                4 : drive_byte(ip_num[7 :0]);
                5 : drive_byte(8'h00);              //Identification
                6 : drive_byte(8'h00);              //Identification
                7 : drive_byte(8'h40);              //Don't fragment
                8 : drive_byte(8'h00);              //Don't fragment
                9 : drive_byte(8'hff);              //Time to live
                10: drive_byte(8'h11);              //Udp protocol
                11: drive_byte(8'haa);              //ip head check sum,there isn't checking for convinent
                12: drive_byte(8'haa);              //ip head check sum,there isn't checking for convinent
                13: drive_byte(RADAR_IP[31:24]);    //source ip
                14: drive_byte(RADAR_IP[23:16]);
                15: drive_byte(RADAR_IP[15: 8]);
                16: drive_byte(RADAR_IP[7 : 0]);
                17: drive_byte(BOARD_IP[31:24]);    //destinate ip
                18: drive_byte(BOARD_IP[23:16]);
                19: drive_byte(BOARD_IP[15: 8]);
                20: drive_byte(BOARD_IP[7 : 0]);
                default: ;
            endcase
        end
        /*----------------  UDP head   ----------------*/
        for (integer i = 1; i <= UDP_HEAD_LEN; i = i + 1 ) begin
            case (i)
                1: drive_byte(src_port[15:8]);              //source port
                2: drive_byte(src_port[7 :0]);              
                3: drive_byte(des_port[15:8]);              //destinate port
                4: drive_byte(des_port[7 :0]);              
                5: drive_byte(udp_num [15:8]);              //udp lengh
                6: drive_byte(udp_num [7 :0]);              
                7: drive_byte(8'haa);                       //udp check sum,
                8: drive_byte(8'haa);              
                default: ;
            endcase
        end
    end
    else begin
        /*----------------  ARP data   ----------------*/
        for (integer i = 1; i <= ARP_LEN; i = i + 1 ) begin
            case (i)
                1 : drive_byte(8'h00);              
                2 : drive_byte(8'h01);               //hardware type:0x0001--eth
                3 : drive_byte(8'h08);       
                4 : drive_byte(8'h00);              //top protocol type:0x0800--ip
                5 : drive_byte(8'h06);              //MAC addr lenght:6
                6 : drive_byte(8'h04);              //IP addr length :4
                7 : drive_byte(8'h00);              
                8 : drive_byte(8'h01);              //OP:0x0001--arp request
                9 : drive_byte(RADAR_MAC[47:40]);              
                10: drive_byte(RADAR_MAC[39:32]);              
                11: drive_byte(RADAR_MAC[31:24]);              
                12: drive_byte(RADAR_MAC[23:16]);              
                13: drive_byte(RADAR_MAC[15:8 ]);              
                14: drive_byte(RADAR_MAC[7 :0 ]);   // source mac addr          
                15: drive_byte(RADAR_IP [31:24]);         
                16: drive_byte(RADAR_IP [23:16]);
                17: drive_byte(RADAR_IP [15: 8]);
                18: drive_byte(RADAR_IP [7 : 0]);    //source ip       

                19: drive_byte(8'hff);              
                20: drive_byte(8'hff);              
                21: drive_byte(8'hff);              
                22: drive_byte(8'hff);              
                23: drive_byte(8'hff);              
                24: drive_byte(8'hff);              // des mac addr          
                25: drive_byte(BOARD_IP[31:24]);         
                26: drive_byte(BOARD_IP[23:16]);
                27: drive_byte(BOARD_IP[15: 8]);
                28: drive_byte(BOARD_IP[7 : 0]);    //source ip       
                default: ;
            endcase
        end
    end
    /*----------------  Data   ----------------*/
    for (integer i = 0; i < len; i = i + 1 ) begin
        drive_byte(data[i][15:8]);
        drive_byte(data[i][7 :0]);
    end
    /*----------------  CRC    ----------------*/
    for (integer i = 1; i <= CRC_LEN; i = i + 1 ) begin
        drive_byte(8'haa);          //not check for convenience
    end
end
endtask //automatic

eth_udp_loop u_eth_udp_loop (
    .sys_rst_n               ( sys_rst_n         ),
    .key                     ( key               ),
    .eth_rxc                 ( eth_rxc           ),
    .eth_rx_ctl              ( eth_rx_ctl        ),
    .eth_rxd                 ( eth_rxd     [3:0] ),

    .eth_txc                 ( eth_txc           ),
    .eth_tx_ctl              ( eth_tx_ctl        ),
    .eth_txd                 ( eth_txd     [3:0] )
    // .eth_rst_n               ( eth_rst_n         )
);

endmodule