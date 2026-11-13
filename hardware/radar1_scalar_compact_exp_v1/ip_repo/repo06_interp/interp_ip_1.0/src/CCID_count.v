`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/03/05 15:37:09
// Design Name: 
// Module Name: ID_float
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module CCID_count(
     input clk,
     input signed [31:0] AQ_data, 
     input signed [31:0] AR_data,
     input wire id_pulse,  
     output reg [15:0] xid,
     output  reg [15:0] yid,
     output wire id_done,
     output [31:0] DATA_FIND_addr,
     output wire addr_done
    );
//parameter a = 32'b00000000000000000000110100011011;//0.0512
//parameter fa_new = 32'b00000101110111111110011001100110;//1503.9
//parameter fa_new = 32'b00000011101111010000100000000011;//V=1.9
//parameter xr_par = 32'b00000110000000100111010111000010;//1538.46
//parameter xr_par = 32'b00000011110011100101101111010111;  //V=1.9
parameter a = 32'b00000000000000000010101110110000;//0.170665
//parameter fa_new = 32'b00000001111101111110100000000011;//V=1
//parameter xr_par = 32'b00000010000000001101001000001100;  //V=1
parameter fa_new = 32'b00000101110111000000000000000000;//V=3.2
parameter xr_par = 32'b00000110011010010000011010001101;//V=3.2
/*计算xid参数*/
 wire [61:0] c;
 wire [30:0] o;
 wire [31:0] s; 
 wire [30:0] add;//若AQ为正数，则为加法
 wire [30:0] sub;//若AQ为负数，则为减法
 wire [31:0] b;
 wire [31:0] p;
 wire [31:0] q;
 wire signed [31:0] x_r;
 wire signed [31:0] x_r_1;
 wire signed [31:0] AQ_compl;
 wire signed [31:0] AR_compl;
 wire [61:0] mul_dout;
 wire [30:0] x_r_30;
 /******************/
 /*计算yid参数*/
 parameter yid_par = 32'b00000000000110000100010110010100;
 wire [61:0] mul1_dout;
 wire [30:0] t;
 wire [31:0] yid_noceil;
 wire [31:0] yid_1;
 wire [31:0] yid_2;
 
 
 /*************/
  //判断x_r是否计算完成
 reg start_xr;
 reg xr_count_en;
 reg xr_count_done;
 reg [3:0] xr_count_cnt=0;
 /********************/
 /*判断xid、yid是否计算完成*/
 reg  start;
 reg  count_en;
 reg  count_done;
 reg [3:0] count_cnt=0;

 /******************/
 /*计算addr参数*/
 reg start_addr;
 reg addr_en;
 reg addr_done;
 reg [3:0] addr_cnt=0;
 wire [35:0] yid_out;
 wire [31:0] DATA_FIND_addr_1;
 /*判断加法与减法是否计算完成*/
reg start_1;
reg addsub_en;
reg addsub_done;
reg [3:0] addsub_cnt=0;
 /*************************/
 /****************/
 /*计算补码与xr*/
assign AQ_compl = (AQ_data[31] == 1'b1)?{1'b1,~AQ_data[30:0]}:AQ_data;
assign x_r_30 = mul_dout >>> 16;
assign x_r_1 = (AQ_data[31]==0)?{1'b0,x_r_30}:{1'b1,x_r_30};
assign x_r = (xr_count_en==1)?x_r_1:x_r;
/*****************/
/*计算xid*/
assign o = c >>> 16;
 assign s = (a[31]==b[31])?{1'b0,o}:{1'b1,o};
 assign q = (x_r[31]==0)?add:sub;
 assign b = (count_en == 1)?q:b;
 assign p = (s[15:0]==16'b0000000000000000)?s[31:16]:(s[31:16] + 1'b1);
 //assign xid = (count_en == 1)? p : xid;
 assign id_done = count_done;
 /*计算yid*/
 assign AR_compl = (AQ_data[31] == 1'b1)?{1'b0,(~AR_data[30:0]+1'b1)}:AR_data;
 assign t = mul1_dout >>> 16; 
assign yid_noceil = (AR_compl[31]==0)?{1'b0,t}:{1'b1,t};
assign yid_1 = (yid_noceil[15:0]==16'b0000000000000000)?yid_noceil[31:16]:(yid_noceil[31:16] + 1'b1);
//assign yid_2 = (count_en == 1)?yid_1 : yid_2;
 /*******/
 /*计算地址*/
 assign   DATA_FIND_addr_1=(xid+yid_out[31:0])<<3; 
 assign DATA_FIND_addr = (addr_en == 1)?DATA_FIND_addr_1:DATA_FIND_addr;
 /***********/
/*****/
always@(*)begin
 if(count_en == 1)
 yid <= yid_1;
 else
 yid <= yid;
 end
always@(*)begin
 if(count_en == 1)
 xid <= p+'d171;
 else
 xid <= xid;
 end
always@(posedge clk)begin
  start_xr<=id_pulse;
  end
 always@(posedge clk)begin
    if(xr_count_done==1)
        xr_count_en<=0;
      else if(start_xr==1)
        xr_count_en<=1; 
        end
 always@(posedge clk)begin
       if(xr_count_en==1 && xr_count_cnt==2) 
          xr_count_done<=1;
        else
          xr_count_done<=0;
          end    
 always@(posedge clk)begin
    if(xr_count_en==1 && xr_count_cnt==2)
        xr_count_cnt<=0;
     else if(xr_count_en==1)
        xr_count_cnt<=xr_count_cnt+1;
        end
 /************/
 always@(posedge clk)begin
    start<=addsub_done;
 end
 always@(posedge clk)begin
    if(count_done==1)
        count_en<=0;
      else if(start==1&&count_done==0)
        count_en<=1;
 end
 
 always@(posedge clk)begin
       if(count_en==1 && count_cnt==2) 
           count_done<=1;
        else
            count_done<=0;
  end
 always@(posedge clk)begin
    if(count_en==1 && count_cnt==2)
        count_cnt<=0;
     else if(count_en==1)
        count_cnt<=count_cnt+1;
 end
 /***************/
 always@(posedge clk)begin
     start_addr <= count_done;
 end
 always@(posedge clk)begin
     if(addr_done==1)
        addr_en<=0;
      else if(start_addr==1&&addr_done==0)
        addr_en<=1;   
     end
 always@(posedge clk)begin
       if(addr_en==1 && addr_cnt==2) 
           addr_done<=1;
        else
            addr_done<=0;
  end
 always@(posedge clk)begin
    if(addr_en==1 && addr_cnt==2)
        addr_cnt<=0;
     else if(addr_en==1)
        addr_cnt<=addr_cnt+1;
 end
/************/
/****************/
always@(posedge clk)begin
     start_1<=xr_count_done;
end
always@(posedge clk)begin
     if(addsub_done==1)
        addsub_en<=0;
      else if(start_1==1&&addsub_done==0)
        addsub_en<=1;   
     end
 always@(posedge clk)begin
       if(addsub_en==1 && addsub_cnt==1) 
           addsub_done<=1;
        else
            addsub_done<=0;
  end 
 always@(posedge clk)begin
    if(addsub_en==1 && addsub_cnt==1)
        addsub_cnt<=0;
     else if(addsub_en==1)
        addsub_cnt<=addsub_cnt+1;
 end
xid_mult_gen_2 u_mul_xid2 (
  .CLK(clk),  // input wire CLK
  .A(a[30:0]),      // input wire [30 : 0] A
  .B(b[30:0]),      // input wire [30 : 0] B
  .CE(count_en),    // input wire CE
  .P(c)      // output wire [61 : 0] P
);
xid_add u_add (
  .A(x_r[30:0]),      // input wire [31 : 0] A
  .B(fa_new[30:0]),      // input wire [31 : 0] B
  .CLK(clk),  // input wire CLK
  .CE(addsub_en),
  .S(add)      // output wire [31 : 0] S
);
xid_sub u_sub (
  .A(fa_new[30:0]),      // input wire [30 : 0] A
  .B(x_r[30:0]),      // input wire [30 : 0] B
  .CLK(clk),  // input wire CLK
  .CE(addsub_en),
  .S(sub)      // output wire [30 : 0] S
);
xid_mult_gen_1 u_mul_xid1 (
  .CLK(clk),  // input wire CLK
  .A(AQ_compl[30:0]),      // input wire [30 : 0] A
  .B(xr_par[30:0]),      // input wire [30 : 0] B
  .CE(xr_count_en),    // input wire CE
  .P(mul_dout)      // output wire [61 : 0] P
);
yid_mult u_multis (
  .CLK(clk),  // input wire CLK
  .A(AR_compl[30:0]),      // input wire [30 : 0] A
  .B(yid_par[30:0]),      // input wire [30 : 0] B
  .CE(count_en),    // input wire CE
  .P(mul1_dout)      // output wire [61 : 0] P
);
addrmul u_addrmul ( //512乘法不需要时钟
 // .CLK(clk),  // input wire CLK
  .A(yid),      // input wire [15 : 0] A
//  .CE(addr_en),    // input wire CE
  .P(yid_out)      // output wire [35 : 0] P
);
endmodule
