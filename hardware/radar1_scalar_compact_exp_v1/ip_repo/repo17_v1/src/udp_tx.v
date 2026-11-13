//****************************************Copyright (c)***********************************//
//原子哥在线教学平台：www.yuanzige.com
//技术支持：www.openedv.com
//淘宝店铺：http://openedv.taobao.com 
//关注微信公众平台微信号："正点原子"，免费获取ZYNQ & FPGA & STM32 & LINUX资料。
//版权所有，盗版必究。
//Copyright(C) 正点原子 2018-2028
//All rights reserved                                  
//----------------------------------------------------------------------------------------
// File name:           udp_tx
// Last modified Date:  2020/2/18 9:20:14
// Last Version:        V1.0
// Descriptions:        以太网数据发送模块
//----------------------------------------------------------------------------------------
// Created by:          正点原子
// Created date:        2020/2/18 9:20:14
// Version:             V1.0
// Descriptions:        The original version
//
//----------------------------------------------------------------------------------------
//****************************************************************************************//

module udp_tx(    
    input                clk        , //时钟信号
    input                rst_n      , //复位信号，低电平有效
    
    input                tx_start_en, //以太网开始发送信号
    input        [31:0]  tx_data    , //以太网待发送数据  
    input        [15:0]  tx_byte_num, //以太网发送的有效字节数
    input        [47:0]  des_mac    , //发送的目标MAC地址
    input        [31:0]  des_ip     , //发送的目标IP地址    
    input        [31:0]  crc_data   , //CRC校验数据
    input         [7:0]  crc_next   , //CRC下次校验完成数据
    output  reg          tx_done    , //以太网发送完成信号
    output  reg          tx_req     , //读数据请求信号
    output  reg          gmii_tx_en , //GMII输出数据有效信号
    output  reg  [7:0]   gmii_txd   , //GMII输出数据
    output  reg          crc_en     , //CRC开始校验使能
    output  reg          crc_clr    ,  //CRC数据复位信号 
    
	input		[111:0]	tx_duanbao,
	input		[7:0]	tx_duanbao_byte_num,
	input	wire		fasong_en
        
//    //--------------------------------------------------------------------------------------------
//    //加入uart,返回网口数据
//    output  reg       uart_done,                //接收一帧数据完成标志
//    output  reg [7:0] uart_data                 //接收的数据    
//    //--------------------------------------------------------------------------------------------
    
    
    );

//parameter define
//开发板MAC地址 00-11-22-33-44-55
parameter BOARD_MAC = 48'h00_11_22_33_44_55;
//开发板IP地址 192.168.1.10   
//parameter BOARD_IP  = {8'd192,8'd168,8'd1,8'd10}; 
parameter BOARD_IP = {8'd192,8'd168,8'd33,8'd30};
//目的MAC地址 ff_ff_ff_ff_ff_ff
parameter  DES_MAC   = 48'hff_ff_ff_ff_ff_ff;
//parameter  DES_MAC   = 48'h0c_22_38_4e_5a_0c;
//目的IP地址 192.168.1.102     
//parameter  DES_IP    = {8'd192,8'd168,8'd1,8'd102};
parameter  DES_IP    = {8'd192,8'd168,8'd33,8'd180};

localparam  st_idle      = 7'b000_0001; //初始状态，等待开始发送信号
localparam  st_check_sum = 7'b000_0010; //IP首部校验和
localparam  st_preamble  = 7'b000_0100; //发送前导码+帧起始界定符
localparam  st_eth_head  = 7'b000_1000; //发送以太网帧头
localparam  st_ip_head   = 7'b001_0000; //发送IP首部+UDP首部
localparam  st_tx_uart_data   = 7'b010_0000; //发送数据
localparam  st_tx_udp_data    = 7'b010_0001; //发送数据
localparam  st_crc       = 7'b100_0000; //发送CRC校验值

localparam  ETH_TYPE     = 16'h0800   ; //以太网协议类型 IP协议
//以太网数据最小46个字节，IP首部20个字节+UDP首部8个字节
//所以数据至少46-20-8=18个字节
localparam  MIN_DATA_NUM = 16'd18     ;  
localparam  UDP_TYPE    = 8'd17       ; //UDP协议类型  

//reg define
reg  [6:0]   cur_state      ;
reg  [6:0]   next_state     ;
                            
reg  [7:0]   preamble[7:0]  ; //前导码
reg  [7:0]   eth_head[13:0] ; //以太网首部
reg  [31:0]  ip_head[6:0]   ; //IP首部 + UDP首部
                            
reg          start_en_d0    ;
reg          start_en_d1    ;
reg          start_en_d2    ;//!
reg          start_en_d3    ;//!
reg  [15:0]  tx_data_num    ; //发送的有效数据字节个数
reg  [15:0]  total_num      ; //总字节数
reg          trig_tx_en     ;
reg  [15:0]  udp_num        ; //UDP字节数
reg          skip_en        ; //控制状态跳转使能信号
reg  [4:0]   cnt            ;
reg  [31:0]  check_buffer   ; //首部校验和
reg  [1:0]   tx_byte_sel    ; //32位数据转8位数据计数器
//reg  [4:0]   tx_byte_sel    ; //32位数据转8位数据计数器
reg  [4:0]   t    ; //!计数器
//reg	 [3:0]	tx_duanbao_bit;//!根据数据byte数确定数据位数

reg  [15:0]  data_cnt       ; //发送数据个数计数器
reg          tx_done_t      ;
reg  [4:0]   real_add_cnt   ; //以太网数据实际多发的字节数
                                    
//wire define                       
wire         pos_start_udp_en    ;//开始发送数据上升沿   UDP触发
wire         pos_start_uart_en    ;//开始发送数据上升沿 uart触发
reg			 udp_tx_flag		 ;
reg			 uart_tx_flag		 ;
wire [15:0]  real_tx_data_num;//实际发送的字节数(以太网最少字节要求)
//*****************************************************
//**                    main code
//*****************************************************

assign  pos_start_udp_en = (~start_en_d1) & start_en_d0;
assign  pos_start_uart_en = (~start_en_d3) & start_en_d2;
assign  real_tx_data_num = (tx_data_num >= MIN_DATA_NUM) 
                           ? tx_data_num : MIN_DATA_NUM; 

//reg		[1:0] fasong_en_cnt;
//reg		      fasong;

//localparam		tx_duanbao = 112'h5aa50b000600be05350c0000aaee;

// always @(posedge clk or negedge rst_n) begin
	// if(!rst_n) begin
		// tx_duanbao_bit <= 8'd111;
	// end
	// else begin
		// tx_duanbao_bit <= tx_duanbao_byte_num * 8'd8 - 8'd1;
	// end
// end

////采tx_start_en的上升沿
//always @(posedge clk or negedge rst_n) begin
//    if(!rst_n) begin
//        fasong_en_cnt <= 1'b0;
//		fasong <= 1'b0;
//    end    
//    else if(fasong_en) begin
//        fasong_en_cnt <= fasong_en_cnt + 1'b1;
//		if(fasong_en_cnt == 2'd3) begin
//			fasong_en_cnt <= 1'b0;
//			fasong <= 1'b1;
//		end
//		else begin
//		    fasong <= 1'b0;
//		end
//    end
//    else begin
//		    fasong <= 1'b0;
//	end
//end
                           
//采tx_start_en的上升沿
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        start_en_d0 <= 1'b0;
        start_en_d1 <= 1'b0;
		start_en_d2 <= 1'b0;
        start_en_d3 <= 1'b0;
    end    
    else begin
        //start_en_d0 <= tx_start_en;
        
		////--------------------------------------------------------------------------------------------
		////start_en_d0 <= fasong;//fasong_en
		
		//start_en_d0 <= fasong_en;
		start_en_d0 <= tx_start_en;      //网口发送触发回传数据
        start_en_d1 <= start_en_d0;
		
		start_en_d2 <= fasong_en;      //uart发送触发回传数据
        start_en_d3 <= start_en_d2;
    end
end 

//寄存数据有效字节
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        tx_data_num <= 16'd0;
        total_num <= 16'd0;
        udp_num <= 16'd0;
		udp_tx_flag		<= 1'b0;
		uart_tx_flag	<= 1'b0;
    end
    else begin
        if(pos_start_udp_en && cur_state==st_idle) begin
            //数据长度
            tx_data_num <= tx_byte_num;
			//tx_data_num <= tx_duanbao_byte_num;			
            //UDP长度：UDP首部长度 + 有效数据            
            udp_num <= tx_byte_num + 16'd8;
			//udp_num <= tx_duanbao_byte_num + 16'd8;
            //IP长度：IP首部长度 + UDP首部 + 有效数据             
            total_num <= tx_byte_num + 16'd20 + 16'd8;
			//total_num <= tx_duanbao_byte_num + 16'd20 + 16'd8;
			udp_tx_flag		<= 1'b1;
			uart_tx_flag	<= 1'b0;
        end
		else if(pos_start_uart_en && cur_state==st_idle) begin
            //数据长度
            //tx_data_num <= tx_byte_num;
			tx_data_num <= tx_duanbao_byte_num;			
            //UDP长度：UDP首部长度 + 有效数据            
            //udp_num <= tx_byte_num + 16'd8;
			udp_num <= tx_duanbao_byte_num + 16'd8;
            //IP长度：IP首部长度 + UDP首部 + 有效数据             
            //total_num <= tx_byte_num + 16'd20 + 16'd8;
			total_num <= tx_duanbao_byte_num + 16'd20 + 16'd8;
			udp_tx_flag		<= 1'b0;
			uart_tx_flag	<= 1'b1;
        end
    end
end

//触发发送信号
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) 
        trig_tx_en <= 1'b0;
    else
        trig_tx_en <= pos_start_udp_en || pos_start_uart_en;

end

always @(posedge clk or negedge rst_n) begin
    if(!rst_n)
        cur_state <= st_idle;  
    else
        cur_state <= next_state;
end

always @(*) begin
    next_state = st_idle;
    case(cur_state)
        st_idle     : begin                               //等待发送数据
            if(skip_en)                
                next_state = st_check_sum;
            else
                next_state = st_idle;
        end  
        st_check_sum: begin                               //IP首部校验
            if(skip_en)
                next_state = st_preamble;
            else
                next_state = st_check_sum;    
        end                             
        st_preamble : begin                               //发送前导码+帧起始界定符
            if(skip_en)
                next_state = st_eth_head;
            else
                next_state = st_preamble;      
        end
        st_eth_head : begin                               //发送以太网首部
            if(skip_en)
                next_state = st_ip_head;
            else
                next_state = st_eth_head;      
        end              
        st_ip_head : begin                                //发送IP首部+UDP首部               
            if(skip_en	&& uart_tx_flag)
                next_state = st_tx_uart_data;
			else if(skip_en	&& udp_tx_flag) begin
				next_state = st_tx_udp_data;
			end
            else
                next_state = st_ip_head;      
        end
        st_tx_uart_data : begin                                //发送数据                  
            if(skip_en)
                next_state = st_crc;
            else
                next_state = st_tx_uart_data;      
        end
		st_tx_udp_data : begin                                //发送数据                  
            if(skip_en)
                next_state = st_crc;
            else
                next_state = st_tx_udp_data;      
        end
        st_crc: begin                                     //发送CRC校验值
            if(skip_en)
                next_state = st_idle;
            else
                next_state = st_crc;      
        end
        default : next_state = st_idle;   
    endcase
end                      

//发送数据
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        skip_en <= 1'b0; 
        cnt <= 5'd0;
        check_buffer <= 32'd0;
        ip_head[1][31:16] <= 16'd0;							//！标识初始化为0，通常每发送一份报文，它的值就会加 1。
        tx_byte_sel <= 2'b0;
		
		t <= 5'd0;
		
        crc_en <= 1'b0;
        gmii_tx_en <= 1'b0;
        gmii_txd <= 8'd0;
        tx_req <= 1'b0;
        tx_done_t <= 1'b0; 
        data_cnt <= 16'd0;
        real_add_cnt <= 5'd0;
        
        //初始化数组    
        //前导码 7个8'h55 + 1个8'hd5
        preamble[0] <= 8'h55;                 
        preamble[1] <= 8'h55;
        preamble[2] <= 8'h55;
        preamble[3] <= 8'h55;
        preamble[4] <= 8'h55;
        preamble[5] <= 8'h55;
        preamble[6] <= 8'h55;
        preamble[7] <= 8'hd5;
        //目的MAC地址
        eth_head[0] <= DES_MAC[47:40];
        eth_head[1] <= DES_MAC[39:32];
        eth_head[2] <= DES_MAC[31:24];
        eth_head[3] <= DES_MAC[23:16];
        eth_head[4] <= DES_MAC[15:8];
        eth_head[5] <= DES_MAC[7:0];
        //源MAC地址
        eth_head[6] <= BOARD_MAC[47:40];
        eth_head[7] <= BOARD_MAC[39:32];
        eth_head[8] <= BOARD_MAC[31:24];
        eth_head[9] <= BOARD_MAC[23:16];
        eth_head[10] <= BOARD_MAC[15:8];
        eth_head[11] <= BOARD_MAC[7:0];
        //以太网类型
        eth_head[12] <= ETH_TYPE[15:8];
        eth_head[13] <= ETH_TYPE[7:0];        
    end
    else begin
        skip_en <= 1'b0;
        tx_req <= 1'b0;
        crc_en <= 1'b0;
        gmii_tx_en <= 1'b0;
        tx_done_t <= 1'b0;
        
        case(next_state)
            st_idle     : begin
                if(trig_tx_en) begin
                    skip_en <= 1'b1; 
                    //版本号：4 首部长度：5(单位:32bit,20byte/4=5)
                    ip_head[0] <= {8'h45,8'h00,total_num};//！total_num，IP数据长度
                    //ip_head[0] <= {8'h45,8'h00,16'd0042};   //!20+8+14=42
                    //16位标识，每次发送累加1      
                    ip_head[1][31:16] <= ip_head[1][31:16] + 1'b1; 
                    //bit[15:13]: 010表示不分片
                    ip_head[1][15:0] <= 16'h4000;    
                    //协议：17(udp)                  
                    ip_head[2] <= {8'h40,UDP_TYPE,16'h0};   
                    //源IP地址               
                    ip_head[3] <= BOARD_IP;
                    //目的IP地址    
                    if(des_ip != 32'd0)						//！des_ip = 32'd0说明src_ip= 32'd0，arp没有接收到源IP地址，arp没发挥作用
                        ip_head[4] <= des_ip;
                    else
                        ip_head[4] <= DES_IP;       		//！arp不发挥作用就直接按照设置好的（电脑）IP地址发过去
                    //16位源端口号：1234  16位目的端口号：1234                      
                    //ip_head[5] <= {16'd1234,16'd1234};  	//！从ip_head[5]开始传UDP首部
					ip_head[5] <= {16'd4096,16'd4096};			//！雷达和FPGA端口号都是4096
                    //16位udp长度，16位udp校验和              
                    ip_head[6] <= {udp_num,16'hc44e};  //！udp_num，udp数据长度，16'h0000是UDP校验和，默认是不做UDP校验的，但是现在要改成做UDP校验，14位短包的校验码是16'hc44a，8位短保的校验码是16'hc444
                    //ip_head[6] <= {16'd0022,16'h0000};//8+14=22
                    //更新MAC地址
                    if(des_mac != 48'b0) begin
                        //目的MAC地址
                        eth_head[0] <= des_mac[47:40];
                        eth_head[1] <= des_mac[39:32];
                        eth_head[2] <= des_mac[31:24];
                        eth_head[3] <= des_mac[23:16];
                        eth_head[4] <= des_mac[15:8];
                        eth_head[5] <= des_mac[7:0];
                    end
                end    
            end                                                       
            st_check_sum: begin                           //IP首部校验，！不校验UDP首部，---》需要改成不做IP首部校验，做UDP首部校验
                cnt <= cnt + 5'd1;
                if(cnt == 5'd0) begin                   
                    check_buffer <= ip_head[0][31:16] + ip_head[0][15:0]
                                    + ip_head[1][31:16] + ip_head[1][15:0]
                                    + ip_head[2][31:16] + ip_head[2][15:0]
                                    + ip_head[3][31:16] + ip_head[3][15:0]
                                    + ip_head[4][31:16] + ip_head[4][15:0];
                end
                else if(cnt == 5'd1)                      //可能出现进位,累加一次
                    check_buffer <= check_buffer[31:16] + check_buffer[15:0];
                else if(cnt == 5'd2) begin                //可能再次出现进位,累加一次
                    check_buffer <= check_buffer[31:16] + check_buffer[15:0];
                end                             
                else if(cnt == 5'd3) begin                //按位取反 
                    skip_en <= 1'b1;
                    cnt <= 5'd0;            
                    //ip_head[2][15:0] <= ~check_buffer[15:0];
                    ip_head[2][15:0] <= 16'h0;              //！不做IP首部校验
                end    
            end              
            st_preamble : begin                           //发送前导码+帧起始界定符
                gmii_tx_en <= 1'b1;
                gmii_txd <= preamble[cnt];
                if(cnt == 5'd7) begin                        
                    skip_en <= 1'b1;
                    cnt <= 5'd0;    
                end
                else    
                    cnt <= cnt + 5'd1;                     
            end
            st_eth_head : begin                           //发送以太网首部
                gmii_tx_en <= 1'b1;
                crc_en <= 1'b1;
                gmii_txd <= eth_head[cnt];
                if (cnt == 5'd13) begin
                    skip_en <= 1'b1;
                    cnt <= 5'd0;
                end    
                else    
                    cnt <= cnt + 5'd1;    
            end                    
            st_ip_head  : begin                           //发送IP首部 + UDP首部 ！cnt0-6,共7个,[31:0]共4Byte，4*7=28Byte（IP首部20Byte，UDP首部8Byte）
                crc_en <= 1'b1;
                gmii_tx_en <= 1'b1;
                tx_byte_sel <= tx_byte_sel + 2'd1;
                if(tx_byte_sel == 2'd0)
                    gmii_txd <= ip_head[cnt][31:24];
                else if(tx_byte_sel == 2'd1)
                    gmii_txd <= ip_head[cnt][23:16];
                else if(tx_byte_sel == 2'd2) begin
                    gmii_txd <= ip_head[cnt][15:8];
                    if(cnt == 5'd6) begin
                        //提前读请求数据，等待数据有效时发送
                        tx_req <= 1'b1;                     
                    end
                end 
                else if(tx_byte_sel == 2'd3) begin
                    gmii_txd <= ip_head[cnt][7:0];  
                    if(cnt == 5'd6) begin
                        skip_en <= 1'b1;   
                        cnt <= 5'd0;
                    end    
                    else
                        cnt <= cnt + 5'd1;  
                end        
            end
           st_tx_uart_data  : begin                           //发送数据
                crc_en <= 1'b1;
                gmii_tx_en <= 1'b1;
                t <= t + 2'd1;  
                if(t == 1'b0) begin
                    //gmii_txd <= tx_data[31:24];
                    //gmii_txd <= 8'h5a;
					gmii_txd <= tx_duanbao[111:111-7];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63:63-7];
                    end
                else if(t == 2'd1) begin
                    //gmii_txd <= tx_data[23:16];
                    //gmii_txd <= 8'ha5;   
					gmii_txd <= tx_duanbao[111-8*1:111-7-8*1];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*1:63-7-8*1];
                    end                
                else if(t == 2'd2) begin
                    //gmii_txd <= tx_data[15:8]8
                    //gmii_txd <= 8'h03;
					gmii_txd <= tx_duanbao[111-8*2:111-7-8*2];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*2:63-7-8*2];
                //    if(data_cnt != tx_data_num - 16'd2)
                //        tx_req <= 1'b1;  
                    end
                else if(t == 2'd3) begin
                    //gmii_txd <= tx_data[7:0];
                    //gmii_txd <= 8'h00;
					gmii_txd <= tx_duanbao[111-8*3:111-7-8*3];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*3:63-7-8*3];
                    end
				else if(t == 5'd4) begin
                    //gmii_txd <= 8'h06;
					gmii_txd <= tx_duanbao[111-8*4:111-7-8*4];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*4:63-7-8*4];
                    end
				else if(t == 5'd5) begin
                    //gmii_txd <= 8'h00;
					gmii_txd <= tx_duanbao[111-8*5:111-7-8*5];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*5:63-7-8*5];
                    end
				else if(t == 5'd6) begin
                    //gmii_txd <= 8'h01;
					gmii_txd <= tx_duanbao[111-8*6:111-7-8*6];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*6:63-7-8*6];
                    end
				else if(t == 5'd7) begin
                    //gmii_txd <= 8'h01;
					gmii_txd <= tx_duanbao[111-8*7:111-7-8*7];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= tx_duanbao[63-8*7:63-7-8*7];
                    end
				else if(t == 5'd8) begin
                    //gmii_txd <= 8'h01;
					gmii_txd <= tx_duanbao[111-8*8:111-7-8*8];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= 8'd0;
                    end
				else if(t == 5'd9) begin
                    //gmii_txd <= 8'h02;
					gmii_txd <= tx_duanbao[111-8*9:111-7-8*9];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= 8'd0;
                    end
				else if(t == 5'd10) begin
                    //gmii_txd <= 8'h03;
					gmii_txd <= tx_duanbao[111-8*10:111-7-8*10];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= 8'd0;
                    end
				else if(t == 5'd11) begin
                    //gmii_txd <= 8'h1e;
					gmii_txd <= tx_duanbao[111-8*11:111-7-8*11];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= 8'd0;
                    end
				else if(t == 5'd12) begin
                    //gmii_txd <= 8'haa;
					gmii_txd <= tx_duanbao[111-8*12:111-7-8*12];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= 8'd0;
                    end
				else if(t == 5'd13) begin
                    //gmii_txd <= 8'hee;
					gmii_txd <= tx_duanbao[111-8*13:111-7-8*13];
					if(tx_duanbao[110] == 1'b0)
						gmii_txd <= 8'd0;
                    end
                //if(data_cnt < tx_data_num - 16'd1)
                //    data_cnt <= data_cnt + 16'd1;                        
                //else if(data_cnt == tx_data_num - 16'd1)begin
				if(data_cnt == 16'd17)begin
                    //如果发送的有效数据少于18个字节，在后面填补充位
                    //补充的值为最后一次发送的有效数据
                //    tx_req <= 1'b0;
                //    if(data_cnt + real_add_cnt < real_tx_data_num - 16'd1)	//real_tx_data_num最小是16'd18
				//	real_add_cnt <= real_add_cnt + 5'd1;  
                //    else begin
                        skip_en <= 1'b1;
                        data_cnt <= 16'd0;
                        real_add_cnt <= 5'd0;
                        t <= 2'd0;                        
                //    end   
                //   if(real_add_cnt > 0) begin
                //        gmii_txd <= 8'd0;
                //    end    
                end
                
                else begin 
                    data_cnt <= data_cnt + 16'd1;
                    //if (t > 5'd13 ) begin
					if (t > tx_duanbao_byte_num - 4'd1 ) begin
                        gmii_txd <= 8'd0;
                    end
                end
                   
            end

			st_tx_udp_data  : begin                           //发送数据
                crc_en <= 1'b1;
                gmii_tx_en <= 1'b1;
                tx_byte_sel <= tx_byte_sel + 2'd1;  
                if(tx_byte_sel == 1'b0)
                    gmii_txd <= tx_data[31:24];
                else if(tx_byte_sel == 2'd1)
                    gmii_txd <= tx_data[23:16];                   
                else if(tx_byte_sel == 2'd2) begin
                    gmii_txd <= tx_data[15:8];   
                    if(data_cnt != tx_data_num - 16'd2)
                        tx_req <= 1'b1;  
                end
                else if(tx_byte_sel == 2'd3)
                    gmii_txd <= tx_data[7:0];    
                if(data_cnt < tx_data_num - 16'd1)
                    data_cnt <= data_cnt + 16'd1;                        
                else if(data_cnt == tx_data_num - 16'd1)begin
                    //如果发送的有效数据少于18个字节，在后面填补充位
                    //补充的值为最后一次发送的有效数据
                    tx_req <= 1'b0;
                    if(data_cnt + real_add_cnt < real_tx_data_num - 16'd1)
                        real_add_cnt <= real_add_cnt + 5'd1;  
                    else begin
                        skip_en <= 1'b1;
                        data_cnt <= 16'd0;
                        real_add_cnt <= 5'd0;
                        tx_byte_sel <= 2'd0;                        
                    end   
                    if(real_add_cnt > 0) begin
                        gmii_txd <= 8'd0;
                    end    
                end   
            end
			
           // st_tx_uart_data  : begin                           //发送数据
                // crc_en <= 1'b1;
                // gmii_tx_en <= 1'b1;
                // tx_byte_sel <= tx_byte_sel + 2'd1;  
                // if(tx_byte_sel == 1'b0) begin gmii_txd <= 8'h5a; end
                // else if(tx_byte_sel == 2'd1) begin gmii_txd <= 8'ha5; end                
                // else if(tx_byte_sel == 2'd2) begin
                    // //gmii_txd <= tx_data[15:8];
                    // gmii_txd <= 8'h03;
                    // //if(data_cnt != tx_data_num - 16'd2)
                    // if(data_cnt != 5'd14 - 16'd2)
                        // tx_req <= 1'b1;  
                    // end
                // else if(tx_byte_sel == 2'd3) begin gmii_txd <= 8'h00; end
                // else if(tx_byte_sel == 5'd4) begin gmii_txd <= 8'h06; end
                // else if(tx_byte_sel == 5'd5) begin gmii_txd <= 8'h00; end
                // else if(tx_byte_sel == 5'd6) begin gmii_txd <= 8'h01; end
                // else if(tx_byte_sel == 5'd7) begin gmii_txd <= 8'h01; end
                // else if(tx_byte_sel == 5'd8) begin gmii_txd <= 8'h01; end
                // else if(tx_byte_sel == 5'd9) begin gmii_txd <= 8'h02; end
                // else if(tx_byte_sel == 5'd10) begin gmii_txd <= 8'h03; end
                // else if(tx_byte_sel == 5'd11) begin gmii_txd <= 8'h1e; end
                // else if(tx_byte_sel == 5'd12) begin gmii_txd <= 8'haa; end
                // else if(tx_byte_sel == 5'd13) begin gmii_txd <= 8'hee; end
                // //if(data_cnt < tx_data_num - 16'd1)
                // if(data_cnt < 5'd14 - 16'd1)
                    // data_cnt <= data_cnt + 16'd1;                        
                // //else if(data_cnt == tx_data_num - 16'd1)begin
                // else if(data_cnt == 5'd14 - 16'd1)begin
                    // //如果发送的有效数据少于18个字节，在后面填补充位
                    // //补充的值为最后一次发送的有效数据
                    // tx_req <= 1'b0;
                    // //if(data_cnt + real_add_cnt < real_tx_data_num - 16'd1)
					// if(data_cnt + real_add_cnt < 5'd15 - 16'd1)
                        // real_add_cnt <= real_add_cnt + 5'd1;  
                    // else begin
                        // skip_en <= 1'b1;
                        // data_cnt <= 16'd0;
                        // real_add_cnt <= 5'd0;
                        // tx_byte_sel <= 2'd0;                        
                    // end   
                    // if(real_add_cnt > 0) begin
                        // gmii_txd <= 8'd0;
                    // end    
                // end   
            // end

//           st_tx_uart_data  : begin                           //发送数据
//                crc_en <= 1'b1;
//                gmii_tx_en <= 1'b1;
//                t <= t+1'd1;
//                gmii_txd <= 8'h5a;
//                skip_en <= 1'b1;
//                case(t)
//					5'd1: begin gmii_txd <= 8'h5a; end
//					5'd2: begin gmii_txd <= 8'ha5; end
//					5'd3: begin gmii_txd <= 8'h03; end
//					5'd4: begin gmii_txd <= 8'h00; end
//					5'd5: begin gmii_txd <= 8'h06; end
//					5'd6: begin gmii_txd <= 8'h00; end
//					5'd7: begin gmii_txd <= 8'h01; end
//					5'd8: begin gmii_txd <= 8'h01; end
//					5'd9: begin gmii_txd <= 8'h01; end
//					5'd10: begin gmii_txd <= 8'h02; end
//					5'd11: begin gmii_txd <= 8'h03; end
//					5'd12: begin gmii_txd <= 8'h1e; end
//					5'd13: begin gmii_txd <= 8'haa; end
//					5'd14: begin gmii_txd <= 8'hee; end
//					5'd15: begin skip_en <= 1'b1; t <= 5'd1; end
//				endcase
				
//				if(data_cnt < tx_data_num - 16'd1)
//                    data_cnt <= data_cnt + 16'd1;                        
//                else if(data_cnt == tx_data_num - 16'd1)begin
//                    //如果发送的有效数据少于18个字节，在后面填补充位
//                    //补充的值为最后一次发送的有效数据
//                    tx_req <= 1'b0;
//                    if(data_cnt + real_add_cnt < real_tx_data_num - 16'd1)
//                        real_add_cnt <= real_add_cnt + 5'd1;  
//                    else begin
//                        skip_en <= 1'b1;
//                        data_cnt <= 16'd0;
//                        real_add_cnt <= 5'd0;
//                        tx_byte_sel <= 2'd0;                        
//                    end   
//                    if(real_add_cnt > 0) begin
//                        gmii_txd <= 8'd0;
//                    end    
//                end
				
//            end
   
            st_crc      : begin                          //发送CRC校验值
                gmii_tx_en <= 1'b1;
                tx_byte_sel <= tx_byte_sel + 2'd1;
                if(tx_byte_sel == 2'd0)
                    gmii_txd <= {~crc_next[0], ~crc_next[1], ~crc_next[2],~crc_next[3],
                                 ~crc_next[4], ~crc_next[5], ~crc_next[6],~crc_next[7]};
                else if(tx_byte_sel == 2'd1)
                    gmii_txd <= {~crc_data[16], ~crc_data[17], ~crc_data[18],~crc_data[19],
                                 ~crc_data[20], ~crc_data[21], ~crc_data[22],~crc_data[23]};
                else if(tx_byte_sel == 2'd2) begin
                    gmii_txd <= {~crc_data[8], ~crc_data[9], ~crc_data[10],~crc_data[11],
                                 ~crc_data[12], ~crc_data[13], ~crc_data[14],~crc_data[15]};                              
                end
                else if(tx_byte_sel == 2'd3) begin
                    gmii_txd <= {~crc_data[0], ~crc_data[1], ~crc_data[2],~crc_data[3],
                                 ~crc_data[4], ~crc_data[5], ~crc_data[6],~crc_data[7]};  
                    tx_done_t <= 1'b1;
                    skip_en <= 1'b1;
                end                                                                                                                                            
            end                          
            default :;  
        endcase                                             
    end
end            

//发送完成信号及crc值复位信号
always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        tx_done <= 1'b0;
        crc_clr <= 1'b0;
    end
    else begin
        tx_done <= tx_done_t;
        crc_clr <= tx_done_t;
    end
end

endmodule

