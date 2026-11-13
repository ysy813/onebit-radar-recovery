`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/04/09 16:43:29
// Design Name: 
// Module Name: fft2_64
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


module fft2_64(
   input wire [73:0] fft2_data,
   output wire [63:0] dataout
    );
assign dataout = fft2_data[63:0];
endmodule
