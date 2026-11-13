`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/09/14 15:08:34
// Design Name: 
// Module Name: fft_saparate
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


module fft_saparate(
input wire [63:0] fft_1ddata,
output wire [31:0] fft_1d_real,
output wire [31:0] fft_1d_img
    );
wire [27:0] real_part;
wire [27:0] img_part;    

assign real_part=fft_1ddata[26:0];
assign img_part=fft_1ddata[58:32];

assign fft_1d_real={{5{real_part[26]}},real_part[26:0]};
assign fft_1d_img={{5{img_part[26]}},img_part[26:0]};

    
endmodule
