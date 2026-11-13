`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/08/31 16:52:49
// Design Name: 
// Module Name: fft_tlast_cnt
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


module fft_tlast_cnt(
input wire clk,
input wire fft_tlast,
input wire fft_valid,
output reg [30:0] fft_valid_cnt,
output wire rd_en,
output reg [30:0] data_valid_cnt,
input wire data_valid,
input wire data_ready,
output wire [10:0] tlast_cnt,
output wire [5:0]  tlast_cnt_cnt,
input wire onewrite_start,
output wire [5:0] onewrite_start_cnt,
input wire oned_fft_valid,
input wire oned_fft_ready,
output reg [30:0] oned_fft_read_cnt,
input wire rstn
    );
reg [10:0] cnt=0;
reg rd_en_reg=0;
reg [12:0] rd_cnt=0;
reg [5:0] tlast_cnt_cnt_reg=0;
reg [5:0] onewrite_cnt=0;
always@(posedge clk) begin
    if(cnt==512)
        cnt<=0;
    else if(fft_tlast==1)
        cnt<=cnt+1;
end    

always@(posedge clk)begin
    if(cnt==512)
        tlast_cnt_cnt_reg<=tlast_cnt_cnt_reg+1;
    else
        tlast_cnt_cnt_reg<=tlast_cnt_cnt_reg;
end


always@(posedge clk)
    if(data_valid && data_ready)
        data_valid_cnt<=data_valid_cnt+1;

always@(posedge clk)begin
    if(fft_valid==1)
        fft_valid_cnt<=fft_valid_cnt+1;
end

assign tlast_cnt=cnt;
assign tlast_cnt_cnt=tlast_cnt_cnt_reg;

always@(posedge clk)begin
    if(onewrite_start==1)
        onewrite_cnt<=onewrite_cnt+1;
end

assign onewrite_start_cnt=onewrite_cnt;

always@(posedge clk)begin
    if(rstn==0)
        oned_fft_read_cnt<=0;
    else if(oned_fft_ready==1 && oned_fft_valid==1)
        oned_fft_read_cnt<=oned_fft_read_cnt+1;   
end


endmodule
