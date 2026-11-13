`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/10/09 14:13:12
// Design Name: 
// Module Name: debug_module
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


module debug_module(
input wire fft2d_valid,
input wire rstn,
input wire clk,
input wire fftshift_w,
input wire frame_end,
output reg [15:0] frame_cnt,
output reg [30:0] fft2d_cnt,
output reg [30:0] fftshift_w_cnt
);

always@(posedge clk)begin
    if(rstn==0)
        fft2d_cnt<=0;
    else if(fft2d_valid==1)
        fft2d_cnt<=fft2d_cnt+1;
end

always@(posedge clk)begin
    if(rstn==0)
        fftshift_w_cnt<=0;
    else if(fftshift_w==1)
        fftshift_w_cnt<=fftshift_w_cnt+1;
end

always@(posedge clk)begin
    if(rstn==0)
        frame_cnt<=0;
    else if(frame_end==1)
        frame_cnt<=frame_cnt+1;
end
endmodule
