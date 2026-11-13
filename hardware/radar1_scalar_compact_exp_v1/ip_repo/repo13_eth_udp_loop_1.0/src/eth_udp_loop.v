//****************************************Copyright (c)***********************************//
//原子哥在线教学平台：www.yuanzige.com
//技术支持：www.openedv.com
//淘宝店铺：http://openedv.taobao.com 
//关注微信公众平台微信号："正点原子"，免费获取ZYNQ & FPGA & STM32 & LINUX资料。
//版权所有，盗版必究。
//Copyright(C) 正点原子 2018-2028
//All rights reserved                                  
//----------------------------------------------------------------------------------------
// File name:           eth_udp_loop
// Last modified Date:  2021/11/23 9:20:14
// Last Version:        V1.0
// Descriptions:        以太网通信UDP通信环回顶层模块
//----------------------------------------------------------------------------------------
// Created by:          正点原子
// Created date:        2021/11/23 9:20:14
// Version:             V1.0
// Descriptions:        The original version 
//
//----------------------------------------------------------------------------------------
//****************************************************************************************//
`include "header.vh"

module eth_udp_loop(
    input              sys_rst_n , //系统复位信号，低电平有效 

    input              key       , //开始发送短包按键
    //以太网RGMII接口   
    input              eth_rxc   , //RGMII接收数据时钟
    input              eth_rx_ctl, //RGMII输入数据有效信号
    input       [3:0]  eth_rxd   , //RGMII输入数据
    output             eth_txc   , //RGMII发送数据时钟    
    output             eth_tx_ctl, //RGMII输出数据有效信号
    output             tx_activity, //GMII TX enable before the RGMII output DDR
    output wire [3:0]   capture_fault,
    output      [3:0]  eth_txd ,    //RGMII输出数据     
    
    output                    axis_clk               ,
    input     wire            fifo2fft_axis_tready,
    output     wire  [31:0]   fifo2fft_axis_tdata ,                      // input wire [31 : 0] s_axis_data_tdata
    output     wire           fifo2fft_axis_tvalid,
    output     wire           fifo2fft_axis_tlast ,          // input wire s_axis_data_tvalid
    output     wire  [12:0]   rd_data_count
    );

//parameter define
parameter  BOARD_MAC = 48'h00_11_22_33_44_55;     
parameter  BOARD_IP  = {8'd192,8'd168,8'd33,8'd30};  
//parameter  DES_MAC   = 48'h12_34_56_78_90_12;      // 雷达MAC
// parameter  DES_MAC   = 48'h20_7b_d2_59_38_5a;        // 电脑USB-ETH MAC
parameter  DES_MAC   = 48'hf4_8e_38_a8_07_90;      // 电脑自带网口 MAC
parameter  DES_IP    = {8'd192,8'd168,8'd33,8'd180};  

parameter SHORT_PK_PORT = 16'd4096;
parameter DATA_PORT     = 16'd4098;

//wire define  
wire          gmii_rx_clk   ; //GMII接收时钟
wire          gmii_rx_dv    ; //GMII接收数据有效信号
wire  [7:0]   gmii_rxd      ; //GMII接收数据
wire          gmii_tx_clk   ; //GMII发送时钟
wire          gmii_tx_en    ; //GMII发送数据使能信号
wire  [7:0]   gmii_txd      ; //GMII发送数据     

wire          arp_gmii_tx_en; //ARP GMII输出数据有效信号 
wire  [7:0]   arp_gmii_txd  ; //ARP GMII输出数据
wire          arp_rx_done   ; //ARP接收完成信号
wire          arp_rx_type   ; //ARP接收类型 0:请求  1:应答
wire  [47:0]  src_mac       ; //接收到目的MAC地址
wire  [31:0]  src_ip        ; //接收到目的IP地址    
wire          arp_tx_en     ; //ARP发送使能信号
wire          arp_tx_type   ; //ARP发送类型 0:请求  1:应答
wire  [47:0]  des_mac       ; //发送的目标MAC地址
wire  [31:0]  des_ip        ; //发送的目标IP地址   
wire          arp_tx_done   ; //ARP发送完成信号

wire          udp_gmii_tx_en; //UDP GMII输出数据有效信号 
wire  [7:0]   udp_gmii_txd  ; //UDP GMII输出数据
(* dont_touch = "true" *) wire          rec_pkt_done  ; //UDP单包数据接收完成信号..
(* dont_touch = "true" *) wire          rec_en        ; //UDP接收的数据使能信号
(* dont_touch = "true" *) wire  [15:0]  rec_data      ; //UDP接收的数据
(* dont_touch = "true" *) wire  [15:0]  rec_byte_num  ; //UDP接收的有效字节数 单位:byte ..
wire  [15:0]  tx_byte_num   ; //UDP发送的有效字节数 单位:byte 
wire          udp_tx_done   ; //UDP发送完成信号
wire          tx_req        ; //UDP读数据请求信号
wire  [31:0]  tx_data       ; //UDP待发送数据

wire          tx_start_en   ; // UDP发送开始使能信号
wire  [15:0]  dst_port      ; // 接收到UDP包的目的端口
wire  [2 :0]  short_pk      ;
wire          clk_250m      ;
wire          clk_50m       ;
wire          key_value     ;
wire          key_flag      ;

(* dont_touch = "true" *) wire               udp2fifo_axis_tready   ;
(* dont_touch = "true" *) wire               udp2fifo_axis_tvalid   ; 
(* dont_touch = "true" *) wire  [31 : 0]     udp2fifo_axis_tdata    ;
(* dont_touch = "true" *) wire               udp2fifo_axis_tlast    ;

(* dont_touch = "true" *) wire               fifo2fft_axis_tvalid   ;
(* dont_touch = "true" *) wire               fifo2fft_axis_tready   ;
(* dont_touch = "true" *) wire  [31 : 0]     fifo2fft_axis_tdata    ;
(* dont_touch = "true" *) wire               fifo2fft_axis_tlast    ;

//wire  [63 : 0]     fft2fft_axis_tdata     ;
//wire  [15  : 0]    fft2fft_axis_tuser     ;
//wire               fft2fft_axis_tvalid    ;
//wire               fft2fft_axis_tready     = 1'b1;
//wire               fft2fft_axis_tlast     ;

wire               event_frame_started         ;
wire               event_tlast_unexpected      ;
wire               event_tlast_missing         ;
wire               event_status_channel_halt   ;
wire               event_data_in_channel_halt  ;
wire               event_data_out_channel_halt ;

wire               clk_125m_deg;

//*****************************************************
//**                    main code
//*****************************************************

// Debug-only observation point. Probe this signal rather than eth_tx_ctl:
// eth_tx_ctl is driven by an ODDRE1 dedicated to the output pin and therefore
// cannot legally fan back into ordinary FPGA fabric/ILA logic.
assign tx_activity = gmii_tx_en;

// assign tx_start_en = rec_pkt_done;
// assign tx_byte_num = rec_byte_num;
assign axis_clk = clk_250m;
assign des_mac = src_mac;
assign des_ip = src_ip;
assign eth_txc = clk_125m_deg;

/**************该计数器仅用于调试***************/
// (* mark_debug = "true" *) reg  [15:0] tx_cnt;
// 
// always @(posedge gmii_rx_clk or negedge sys_rst_n) begin
//     if(!sys_rst_n) 
//         tx_cnt <= 'd0;
//     else if(tx_start_en)
//         tx_cnt <= tx_cnt + 1'b1;           
// end
/****************************************/

//MMCM/PLL
clk_wiz u_clk_wiz(
  // Clock out ports
  .clk_out1   (clk_125m_deg),       // output clk_out1
  .clk_out2   (clk_250m    ),
  .clk_out3   (clk_50m     ),
  // Status and control signals
  .reset      (~sys_rst_n  ),       // input reset
  .locked     (locked      ),       // output locked
 // Clock in ports
  .clk_in1    (rgmii_txc   )        // input clk_in1
  );
  

//GMII接口转RGMII接口
gmii_to_rgmii u_gmii_to_rgmii(
    .gmii_rx_clk   (gmii_rx_clk ),
    .gmii_rx_dv    (gmii_rx_dv  ),
    .gmii_rxd      (gmii_rxd    ),
    .gmii_tx_clk   (gmii_tx_clk ),
    .gmii_tx_en    (gmii_tx_en  ),
    .gmii_txd      (gmii_txd    ),
    
    .rgmii_rxc     (eth_rxc     ),  
    .rgmii_rx_ctl  (eth_rx_ctl  ),
    .rgmii_rxd     (eth_rxd     ),
    .rgmii_txc     (rgmii_txc   ),
    .rgmii_tx_ctl  (eth_tx_ctl  ),
    .rgmii_txd     (eth_txd     )
    );

//ARP通信
arp                                             
   #(
    .BOARD_MAC     (BOARD_MAC),      //参数例化
    .BOARD_IP      (BOARD_IP ),
    .DES_MAC       (DES_MAC  ),
    .DES_IP        (DES_IP   )
    )
   u_arp(
    .rst_n         (sys_rst_n  ),
                    
    .gmii_rx_clk   (gmii_rx_clk),
    .gmii_rx_dv    (gmii_rx_dv ),
    .gmii_rxd      (gmii_rxd   ),
    .gmii_tx_clk   (gmii_tx_clk),
    .gmii_tx_en    (arp_gmii_tx_en ),
    .gmii_txd      (arp_gmii_txd),
                    
    .arp_rx_done   (arp_rx_done),
    .arp_rx_type   (arp_rx_type),
    .src_mac       (src_mac    ),
    .src_ip        (src_ip     ),
    .arp_tx_en     (arp_tx_en  ),
    .arp_tx_type   (arp_tx_type),
    .des_mac       (des_mac    ),
    .des_ip        (des_ip     ),
    .tx_done       (arp_tx_done)
    );

//UDP通信
udp                                             
   #(
    .SHORT_PK_PORT (SHORT_PK_PORT),
    .BOARD_MAC     (BOARD_MAC),      //参数例化
    .BOARD_IP      (BOARD_IP ),
    .DES_MAC       (DES_MAC  ),
    .DES_IP        (DES_IP   )
    )
   u_udp(
    .rst_n         (sys_rst_n   ),  

    .key           (key_value   ),
    
    .gmii_rx_clk   (gmii_rx_clk ),           
    .gmii_rx_dv    (gmii_rx_dv  ),         
    .gmii_rxd      (gmii_rxd    ),                   
    .gmii_tx_clk   (gmii_tx_clk ), 
    .gmii_tx_en    (udp_gmii_tx_en),         
    .gmii_txd      (udp_gmii_txd),  

    .rec_pkt_done  (rec_pkt_done),    
    .rec_en        (rec_en      ),     
    .rec_data      (rec_data    ),         
    .rec_byte_num  (rec_byte_num),      
    .tx_start_en   (tx_start_en ),        
    // .tx_data       (tx_data     ),         
    // .tx_byte_num   (tx_byte_num ),  
    .des_mac       (des_mac     ),
    .des_ip        (des_ip      ),    
    .tx_done       (udp_tx_done ),        
    // .tx_req        (tx_req      ) 
    
    .dst_port      (dst_port    )
    );  

async_fifo_128x32 u_async_fifo_128x32 (
    .m_aclk            (clk_250m),               // input wire m_aclk
    .s_aclk            (gmii_rx_clk),            // input wire s_aclk
    .s_aresetn         (sys_rst_n),              // input wire s_aresetn
    .s_axis_tvalid     (udp2fifo_axis_tvalid),   // input wire s_axis_tvalid
    .s_axis_tready     (udp2fifo_axis_tready),   // output wire s_axis_tready
    .s_axis_tdata      (udp2fifo_axis_tdata),    // input wire [127 : 0] s_axis_tdata
    //.s_axis_tlast      (udp2fifo_axis_tlast),    // input wire s_axis_tlast
            
    .m_axis_tvalid     (fifo2fft_axis_tvalid),   // output wire m_axis_tvalid
    .m_axis_tready     (fifo2fft_axis_tready),   // input wire m_axis_tready
    .m_axis_tdata      (fifo2fft_axis_tdata),    // output wire [127 : 0] m_axis_tdata
    .axis_rd_data_count(rd_data_count)  // output wire [12 : 0] axis_rd_data_count
    //.m_axis_tlast      (fifo2fft_axis_tlast)     // output wire m_axis_tlast
);


//以太网控制模块
eth_ctrl u_eth_ctrl(
    .clk            (gmii_rx_clk),
    .rst_n          (sys_rst_n),

    .arp_rx_done    (arp_rx_done   ),
    .arp_rx_type    (arp_rx_type   ),
    .arp_tx_en      (arp_tx_en     ),
    .arp_tx_type    (arp_tx_type   ),
    .arp_tx_done    (arp_tx_done   ),
    .arp_gmii_tx_en (arp_gmii_tx_en),
    .arp_gmii_txd   (arp_gmii_txd  ),
    
    .udp_tx_start_en(tx_start_en   ),
    .udp_tx_done    (udp_tx_done   ),    
    .udp_gmii_tx_en (udp_gmii_tx_en),
    .udp_gmii_txd   (udp_gmii_txd  ),
                     
    .gmii_tx_en     (gmii_tx_en    ),
    .gmii_txd       (gmii_txd      )
    );

native2axis #(
    .DATA_PORT            ( 4098  ),
    .C_M_AXIS_TDATA_WIDTH ( 32   ),
    .C_M_START_COUNT      ( 32    ))
    u_native2axis (
    .rec_data                ( rec_data         ),
    .rec_en                  ( rec_en           ),
    .rec_pkt_done            ( rec_pkt_done     ),
    .dst_port                ( dst_port         ),
    .M_AXIS_ACLK             ( gmii_rx_clk      ),
    .M_AXIS_ARESETN          ( sys_rst_n   ),
    .M_AXIS_TREADY           ( udp2fifo_axis_tready    ),

    .M_AXIS_TVALID           ( udp2fifo_axis_tvalid    ),
    .M_AXIS_TDATA            ( udp2fifo_axis_tdata     ),
    .M_AXIS_TLAST            ( udp2fifo_axis_tlast     ),
    .capture_fault           ( capture_fault          )
);

// xfft_0 u_fft_0 (
//     .aclk                           (clk_250m ),                                                // input wire aclk
//     .aresetn                        (sys_rst_n),                                          // input wire aresetn
//     .s_axis_config_tdata            (8'd1),                  // input wire [15 : 0] s_axis_config_tdata
//     .s_axis_config_tvalid           (1'b1 ),                // input wire s_axis_config_tvalid
//     .s_axis_config_tready           (     ),                // output wire s_axis_config_tready
//     .s_axis_data_tdata              (fifo2fft_axis_tdata ),                      // input wire [127 : 0] s_axis_data_tdata
//     .s_axis_data_tvalid             (fifo2fft_axis_tvalid),                    // input wire s_axis_data_tvalid
//     .s_axis_data_tready             (fifo2fft_axis_tready),                    // output wire s_axis_data_tready
//     .s_axis_data_tlast              (fifo2fft_axis_tlast ),                      // input wire s_axis_data_tlast

//     .m_axis_data_tdata              (fft2fft_axis_tdata ),                      // output wire [255 : 0] m_axis_data_tdata
//     .m_axis_data_tuser              (fft2fft_axis_tuser ),                      // output wire [7 : 0] m_axis_data_tuser
//     .m_axis_data_tvalid             (fft2fft_axis_tvalid),                    // output wire m_axis_data_tvalid
//     .m_axis_data_tready             (fft2fft_axis_tready),                    // input wire m_axis_data_tready
//     .m_axis_data_tlast              (fft2fft_axis_tlast ),                      // output wire m_axis_data_tlast

//     .event_frame_started            (event_frame_started        ),                  // output wire event_frame_started
//     .event_tlast_unexpected         (event_tlast_unexpected     ),            // output wire event_tlast_unexpected
//     .event_tlast_missing            (event_tlast_missing        ),                  // output wire event_tlast_missing
//     .event_status_channel_halt      (event_status_channel_halt  ),      // output wire event_status_channel_halt
//     .event_data_in_channel_halt     (event_data_in_channel_halt ),    // output wire event_data_in_channel_halt
//     .event_data_out_channel_halt    (event_data_out_channel_halt)  // output wire event_data_out_channel_halt
// );
//xfft_0 u_fft_0 (
//  .aclk(clk_250m),                                                // input wire aclk
//  .aresetn(sys_rst_n),                                          // input wire aresetn
//  .s_axis_config_tdata (8'd1),                                    // input wire [7 : 0] s_axis_config_tdata
//  .s_axis_config_tvalid(1'b1),                                  // input wire s_axis_config_tvalid
//  .s_axis_config_tready(    ),                                  // output wire s_axis_config_tready
//  .s_axis_data_tdata (fifo2fft_axis_tdata ),                      // input wire [31 : 0] s_axis_data_tdata
//  .s_axis_data_tvalid(fifo2fft_axis_tvalid),                    // input wire s_axis_data_tvalid
//  .s_axis_data_tready(fifo2fft_axis_tready),                    // output wire s_axis_data_tready
//  .s_axis_data_tlast (fifo2fft_axis_tlast ),                      // input wire s_axis_data_tlast

//  .m_axis_data_tdata (fft2fft_axis_tdata),                      // output wire [63 : 0] m_axis_data_tdata
//  .m_axis_data_tuser (fft2fft_axis_tuser),                      // output wire [15 : 0] m_axis_data_tuser
//  .m_axis_data_tvalid(fft2fft_axis_tvalid),                    // output wire m_axis_data_tvalid
//  .m_axis_data_tready(fft2fft_axis_tready),                    // input wire m_axis_data_tready
//  .m_axis_data_tlast (fft2fft_axis_tlast),                      // output wire m_axis_data_tlast

//  .event_frame_started        (event_frame_started),                  // output wire event_frame_started
//  .event_tlast_unexpected     (event_tlast_unexpected),            // output wire event_tlast_unexpected
//  .event_tlast_missing        (event_tlast_missing),                  // output wire event_tlast_missing
//  .event_status_channel_halt  (event_status_channel_halt),      // output wire event_status_channel_halt
//  .event_data_in_channel_halt (event_data_in_channel_halt),    // output wire event_data_in_channel_halt
//  .event_data_out_channel_halt(event_data_out_channel_halt)  // output wire event_data_out_channel_halt
//);

key_debounce  u_key_debounce (
    .sys_clk                 ( clk_50m     ),
    .sys_rst_n               ( sys_rst_n   ),
    .key                     ( key         ),

    .key_value               ( key_value   ),
    .key_flag                ( key_flag    )
);

`ifdef SIMULATION
(* dont_touch = "true" *) reg  [32: 0] abs_fft_out;
(* dont_touch = "true" *) wire [31: 0] abs_real, abs_imag;    //..
assign abs_real = fft2fft_axis_tdata[31] ? ~(fft2fft_axis_tdata[31: 0]-1'b1) : fft2fft_axis_tdata[31: 0];
assign abs_imag = fft2fft_axis_tdata[63] ? ~(fft2fft_axis_tdata[63:32]-1'b1) : fft2fft_axis_tdata[63:32];
always @(posedge clk_250m) begin
    abs_fft_out <= abs_real + abs_imag;
end 
`endif 

`ifdef ILA_EN
(* dont_touch = "true" *) reg  [32: 0] abs_fft_out;
(* dont_touch = "true" *) wire [31: 0] abs_real, abs_imag;    //..
assign abs_real = fft2fft_axis_tdata[31] ? ~(fft2fft_axis_tdata[31: 0]-1'b1) : fft2fft_axis_tdata[31: 0];
assign abs_imag = fft2fft_axis_tdata[63] ? ~(fft2fft_axis_tdata[63:32]-1'b1) : fft2fft_axis_tdata[63:32];
always @(posedge clk_250m) begin
    abs_fft_out <= abs_real + abs_imag;
end 

`endif 



// `ifdef SIMULATION
// integer abs_file_real, abs_file_imag, err, read_code;
// reg [320:0] str;
// initial begin
//     abs_file_real = $fopen("./fft_abs_real.txt", "w");
//     err = $ferror(abs_file_real, str);
//     $display("Error number is: %h (real).", err );  //0
//     $display("Error info is: %s(real).", str );    //0

//     abs_file_imag = $fopen("./fft_abs_imag.txt", "w");
//     err = $ferror(abs_file_imag, str);
//     $display("Error number is: %h (imag).", err );  //0
//     $display("Error info is: %s (imag).", str );    //0
// end

// always @(posedge clk_250m) begin
//     if(fft2fft_axis_tvalid) begin
//         $fdisplay(abs_file_real,"%d",$signed(fft2fft_axis_tdata[31:0]));
//         $fdisplay(abs_file_imag,"%d",$signed(fft2fft_axis_tdata[63:32]));
//     end
// end
// `endif 

endmodule
