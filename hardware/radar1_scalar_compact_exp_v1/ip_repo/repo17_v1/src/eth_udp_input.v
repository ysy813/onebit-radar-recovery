//****************************************Copyright (c)***********************************//
//ԭ�Ӹ����߽�ѧƽ̨��www.yuanzige.com
//����֧�֣�www.openedv.com
//�Ա����̣�http://openedv.taobao.com 
//��ע΢�Ź���ƽ̨΢�źţ�"����ԭ��"����ѻ�ȡZYNQ & FPGA & STM32 & LINUX���ϡ�
//��Ȩ���У�����ؾ���
//Copyright(C) ����ԭ�� 2018-2028
//All rights reserved                                  
//----------------------------------------------------------------------------------------
// File name:           eth_udp_loop
// Last modified Date:  2021/11/23 9:20:14
// Last Version:        V1.0
// Descriptions:        ͨ����̫��UDP���״﷢�Ͷ̰�������������
//----------------------------------------------------------------------------------------
// Created by:          ����ԭ��
// Created date:        2021/11/23 9:20:14
// Version:             V1.0
// Descriptions:        The original version 
//
//----------------------------------------------------------------------------------------
//****************************************************************************************//

//ͨ����̫��UDP���״﷢�Ͷ̰�������������
module eth_udp_input(
    // input               sys_clk_p ,           //ϵͳ�������ʱ��
    // input               sys_clk_n ,           //ϵͳ�������ʱ��
 
    input               sys_rst_n , //ϵͳ��λ�źţ��͵�ƽ��Ч 
    //��̫��RGMII�ӿ�   
    input               eth_rxc   , //RGMII��������ʱ��
    input               eth_rx_ctl, //RGMII����������Ч�ź�
    input        [3:0]  eth_rxd   , //RGMII��������
    output              eth_txc   , //RGMII��������ʱ��    
    output              eth_tx_ctl, //RGMII���������Ч�ź�
    output       [3:0]  eth_txd   ,  //RGMII�������          

    input               key0      ,            //����
    output  reg  [1:0]  led       ,       //LED��

    input           fft_tready_s  ,
    output          fft_tvalid_s  ,
    output  [127:0] fft_tdata_s   ,
    output          fft_tlast_s   ,

    output          clk_250m      ,
    output          fft_rst_n     ,
    output          clk_50m       //clk_50m

    // output          pixel_clk         ,
    // output          pixel_clk_5x      ,
    // output          pixel_clk_2_5x    ,
    // output          clk_locked        

    );

//----------------//������
// wire     [15:0]  ch0_abs_2d       ;//������
// wire     [15:0]  ch0_re_2d        ; 
// wire     [15:0]  ch0_im_2d        ;
// wire             clk_250m         ;
// wire             m_fft_tvalid_2d  ;
//-----------------

// wire        clk_50m     ;       //50M

//****************************************************************************************//
//ģ�����ţ�����
//****************************************************************************************//

//parameter define
//������MAC��ַ 00-11-22-33-44-55
parameter  BOARD_MAC = 48'h00_11_22_33_44_55;     
//������IP��ַ 192.168.1.10
parameter  BOARD_IP  = {8'd192,8'd168,8'd33,8'd30};  
//Ŀ��MAC��ַ ff_ff_ff_ff_ff_ff
parameter  DES_MAC   = 48'hff_ff_ff_ff_ff_ff;    
//Ŀ��IP��ַ 192.168.1.102     
parameter  DES_IP    = {8'd192,8'd168,8'd33,8'd180};  

//wire define  
wire          gmii_rx_clk   ; //GMII����ʱ��
wire          gmii_rx_dv    ; //GMII����������Ч�ź�
wire  [7:0]   gmii_rxd      ; //GMII��������
wire          gmii_tx_clk   ; //GMII����ʱ��
wire          gmii_tx_en    ; //GMII��������ʹ���ź�
wire  [7:0]   gmii_txd      ; //GMII��������     

wire          arp_gmii_tx_en; //ARP GMII���������Ч�ź� 
wire  [7:0]   arp_gmii_txd  ; //ARP GMII�������
wire          arp_rx_done   ; //ARP��������ź�
wire          arp_rx_type   ; //ARP�������� 0:����  1:Ӧ��
wire  [47:0]  src_mac       ; //���յ�Ŀ��MAC��ַ
wire  [31:0]  src_ip        ; //���յ�Ŀ��IP��ַ    
wire          arp_tx_en     ; //ARP����ʹ���ź�
wire          arp_tx_type   ; //ARP�������� 0:����  1:Ӧ��
wire  [47:0]  des_mac       ; //���͵�Ŀ��MAC��ַ
wire  [31:0]  des_ip        ; //���͵�Ŀ��IP��ַ   
wire          arp_tx_done   ; //ARP��������ź�

wire          udp_gmii_tx_en; //UDP GMII���������Ч�ź� 
wire  [7:0]   udp_gmii_txd  ; //UDP GMII�������
wire          rec_pkt_done  ; //UDP�������ݽ�������ź�
wire          rec_en        ; //UDP���յ�����ʹ���ź�
wire  [31:0]  rec_data      ; //UDP���յ�����
wire  [15:0]  rec_byte_num  ; //UDP���յ���Ч�ֽ��� ��λ:byte 
wire  [15:0]  tx_byte_num   ; //UDP���͵���Ч�ֽ��� ��λ:byte 
wire          udp_tx_done   ; //UDP��������ź�
wire          tx_req        ; //UDP�����������ź�
wire  [31:0]  tx_data       ; //UDP����������

//****************************************************************************************//
//ģ�����ţ�������LED���̰�����
//****************************************************************************************//

wire               key0_value;         //key0������İ���ֵ
wire               key0_flag;          //key0������İ���ֵ��Ч��־

//reg define
reg [26:0] cnt;                           //������

wire			tx_udp_en;
wire [111:0]		tx_duanbao;
wire [7:0]		tx_duanbao_byte_num;

//****************************************************************************************//
//ģ�����ţ�8bit ת 128bit
//****************************************************************************************//

wire  [7:0]   udp_data      ;  //���˺��UDP����
wire          udp_data_vld  ;  //���˺��UDP���ݵ���Ч�ź�

//*********************************************************************************************************************************************//
//**                    main code
//*********************************************************************************************************************************************//

//****************************************************************************************//
//ģ�����ƣ����ڡ�arp udp udp���ݹ��ˡ�
//****************************************************************************************//

assign tx_start_en = rec_pkt_done;
assign tx_byte_num = rec_byte_num;
assign des_mac = src_mac;
assign des_ip = src_ip;
assign eth_txc = clk_125m_deg;

/**************�ü����������ڵ���***************/
// (* mark_debug = "true" *) reg  [15:0] tx_cnt;
// 
// always @(posedge gmii_rx_clk or negedge sys_rst_n) begin
//     if(!sys_rst_n) 
//         tx_cnt <= 'd0;
//     else if(tx_start_en)
//         tx_cnt <= tx_cnt + 1'b1;           
// end
/****************************************/

// //ת������ź�
// IBUFDS diff_clock
// (
//     .I (sys_clk_p),    //ϵͳ�������ʱ��100M
//     .IB(sys_clk_n),    //ϵͳ�������ʱ��100M
//     .O (sys_clk)       //���ϵͳʱ��100M
// ); 

//MMCM/PLL
clk_wiz u_clk_wiz(
  // Clock out ports
  .clk_out1   (clk_125m_deg),       // output clk_out1
  // Status and control signals
  .reset      (~sys_rst_n  ),       // input reset
  .locked     (locked      ),       // output locked
 // Clock in ports
  .clk_in1    (rgmii_txc   )        // input clk_in1
  );

clk_wiz_gmii u_clk_wiz_gmii(
  // Clock out ports
  .clk_out1(clk_250m),     // output clk_out1
  .clk_out2(clk_50m    ),  // output clk_out4   50M     //clk_50m
  // Status and control signals
  .locked(fft_rst_n),       // output locked
  // Clock in ports
  .clk_in1(gmii_rx_clk)       // input clk_in1
  );      

// clk_wiz_display u_clk_wiz_display(
//   // Clock out ports
//   .clk_out1     (pixel_clk),     // output clk_out1 pixel_clk
//   .clk_out2     (pixel_clk_5x),     // output clk_out2 pixel_clk��5��ʱ��
//   .clk_out3     (pixel_clk_2_5x),     // output clk_out3 pixel_clk��2.5��ʱ��
//   // Status and control signals
//   .reset        (~sys_rst_n), // input reset
//   .locked       (clk_locked),       // output locked
//   // Clock in ports
//   .clk_in1_p    (sys_clk_p),      
//   .clk_in1_n    (sys_clk_n)
//   );    

//GMII�ӿ�תRGMII�ӿ�
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

//ARPͨ��
arp                                             
   #(
    .BOARD_MAC     (BOARD_MAC),      //��������
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

//UDPͨ��
udp                                             
   #(
    .BOARD_MAC     (BOARD_MAC),      //��������
    .BOARD_IP      (BOARD_IP ),
    .DES_MAC       (DES_MAC  ),
    .DES_IP        (DES_IP   )
    )
   u_udp(
    .rst_n         (sys_rst_n   ),  
    
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

    // .tx_start_en   (tx_start_en ),   //����ԭ�����̵�udp����fifo
    .tx_start_en   (1'b0 ),

    .tx_data       (tx_data     ),         
    .tx_byte_num   (tx_byte_num ),  
    .des_mac       (des_mac     ),
    .des_ip        (des_ip      ),    
    .tx_done       (udp_tx_done ),        
    .tx_req        (tx_req      ),

// UDP���ݹ���
    .udp_data      (udp_data    ),
    .udp_data_vld  (udp_data_vld),
    
    .tx_duanbao	   (tx_duanbao  ),
	.tx_duanbao_byte_num	(tx_duanbao_byte_num),
	.fasong_en	   (tx_udp_en   )

    );  

//��̫������ģ��
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

//****************************************************************************************//
//ģ�����ƣ�����������LED���̰�����
//****************************************************************************************//



//������
always @ (posedge clk_50m or negedge fft_rst_n) begin   //clk_50m
    if(!fft_rst_n)
        cnt <= 27'd0;
    else if(cnt < 27'd2500_0000)  //����500ms  d2500_0000
        cnt <= cnt + 1'b1;
    else
        cnt <= 27'd0;
end

//ÿ��500ms�͸���LED����˸״̬
always @ (posedge clk_50m or negedge fft_rst_n) begin   //clk_50m
    if(!fft_rst_n)
        led <= 2'b11;
    else if((key0_flag == 1'b1) && (key0_value == 1'b0))
        led[1] <= ~led[1];
    else if(cnt == 27'd2500_0000)   //d2500_0000
        led[0] <= ~led[0];
end

//������������ģ��
key_debounce  u_key0_debounce(
    .sys_rst_n  (fft_rst_n ),
    .clk        (clk_50m   ),       //clk_50m
    .key        (key0      ),
    .key_value  (key0_value),
    .key_flag   (key0_flag )    
    );

duan_bao_send  u_duan_bao_send(
    .sys_clk                (clk_50m),      //clk_50m
    .sys_rst_n              (fft_rst_n),

    .key_value              (key0_value),
    .key_flag               (key0_flag),
    
    .tx_udp_en              (tx_udp_en),
	.tx_duanbao		        (tx_duanbao),
	.tx_duanbao_byte_num	(tx_duanbao_byte_num)
    );

bit8to128 u_bit8to128 (
    .clk           (gmii_rx_clk),
    .clk_m         (clk_250m   ),
    .rst_n         (sys_rst_n  ),
    .wr_vld        (udp_data_vld),
    .wr_data       (udp_data),
    
    .re_tready     (fft_tready_s),
    .re_tvalid     (fft_tvalid_s),
    .re_data       (fft_tdata_s),
    .re_tlast      (fft_tlast_s)
    );

endmodule
