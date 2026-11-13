//****************************************Copyright (c)***********************************//
//原子哥在线教学平台：www.yuanzige.com
//技术支持：www.openedv.com
//淘宝店铺：http://openedv.taobao.com
//关注微信公众平台微信号："正点原子"，免费获取ZYNQ & FPGA & STM32 & LINUX资料。
//版权所有，盗版必究。
//Copyright(C) 正点原子 2018-2028
//All rights reserved
//----------------------------------------------------------------------------------------
// File name:           key_debounce
// Last modified Date:  2019/4/14 16:23:36
// Last Version:        V1.0
// Descriptions:        蜂鸣器控制
//----------------------------------------------------------------------------------------
// Created by:          正点原子
// Created date:        2019/4/14 16:23:36
// Version:             V1.0
// Descriptions:        The original version
//
//----------------------------------------------------------------------------------------
// Modified by:		    正点原子
// Modified date:
// Version:
// Descriptions:
//
//----------------------------------------------------------------------------------------
//****************************************************************************************//

module duan_bao_send(
    input        sys_clk,
    input        sys_rst_n,

    input        key_value,
    input        key_flag,
    
    output	reg			tx_udp_en,			//！UDP发送使能
	output	reg	[111:0]	tx_duanbao,			//！传给udp发送
	output	reg	[7:0]	tx_duanbao_byte_num //！传给udp发送,让它知道需要发送的数据byte数
    );

localparam  U0  =   4'b0010;            // !用于代替tx_data为0,1,2,3
localparam  U1  =   4'b0100;
localparam  U2  =   4'b0110;
localparam  U3  =   4'b1000;
localparam  U4  =   4'b1010;
localparam  U5  =   4'b1100;
localparam  U6  =   4'b1110;            //end

//reg define
reg [23:0] counter;
reg [ 3:0] count;
reg [ 3:0] count_zancun;
reg         flag;

//*****************************************************
//**                    main code
//*****************************************************

//计数器对系统时钟计数，计时0.2秒，仿真时设为10
always @(posedge sys_clk or negedge sys_rst_n) begin
    if (!sys_rst_n)
        counter <= 24'd0;
    else if (counter < 24'd1000_0000)
    // else if (counter < 24'd30)        //仅用于仿真24'd9
        counter <= counter + 1'b1;
    else
        counter <= 24'd0;
end

always @ (posedge sys_clk or negedge sys_rst_n) begin
    if(!sys_rst_n)
        flag <= 1'b0;
    else if((key_flag == 1'b1) && (key_value == 1'b0))  //确保按键key0确实被有效按下
        flag <= 1'b1;
    else if(count == U6)
        flag <= 1'b0;
end

always @(posedge sys_clk or negedge sys_rst_n) begin
    if (!sys_rst_n)
        count <= 4'b0000;
    else if((flag == 1'b1) && (counter == 24'd1000_0000))
    // else if((flag == 1'b1) && (counter == 24'd30))        //仅用于仿真
        count <= count + 1'b1;
    else if((flag == 1'b0) && (count == U6))
        count <= 4'b0000;
end

//每次按键按下时，就翻转蜂鸣器的状态
always @ (posedge sys_clk or negedge sys_rst_n) begin
    if(!sys_rst_n) begin
        tx_duanbao <= 112'h0;
		tx_duanbao_byte_num <= 8'd14;
		tx_udp_en	<=	1'b0;
        count_zancun <= 4'b0000;
		end	
    else if((flag == 1'b1)  && (count_zancun != count)) begin
            case(count)
                U0:begin
                    tx_duanbao <= 112'h5aa50300060001010102031eaaee;
                    tx_duanbao_byte_num <= 8'd14;
                    tx_udp_en	<=	1'b1;
                    count_zancun <= count;
                end
                U1:begin
                    tx_duanbao <= 112'h5aa50e000000aaee;//112'h5aa50300060001010102031eaaee;
                    tx_duanbao_byte_num <= 8'd8;
                    tx_udp_en	<=	1'b1;
                    count_zancun <= count;
                end
                U2:begin
                    tx_duanbao <= 112'h5aa50300060001010102031eaaee;//112'h5aa50b000600be05350c0000aaee
                    tx_duanbao_byte_num <= 8'd14;
                    tx_udp_en	<=	1'b1;
                    count_zancun <= count;
                end
                U3:begin
                    tx_duanbao <= 112'h5aa50300060001010102031eaaee;
                    tx_duanbao_byte_num <= 8'd14;
                    tx_udp_en	<=	1'b1;
                    count_zancun <= count;
                end
                U4:begin
                    tx_duanbao <= 112'h5aa50b000600be05350c0000aaee;
                    tx_duanbao_byte_num <= 8'd14;
                    tx_udp_en	<=	1'b1;
                    count_zancun <= count;
                end
                U5:begin
                    tx_duanbao <= 112'h5aa505000000aaee;
                    tx_duanbao_byte_num <= 8'd8;
                    tx_udp_en	<=	1'b1;
                    count_zancun <= count;
                end
                U6:begin 
                    count_zancun <= count;
                    end
                default : ;
            endcase
        end
        else
            tx_udp_en	<=	1'b0;
end

endmodule
