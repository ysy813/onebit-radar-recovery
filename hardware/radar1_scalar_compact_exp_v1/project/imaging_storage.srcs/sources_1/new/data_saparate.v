`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/09/02 20:58:34
// Design Name: 
// Module Name: data_saparate
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


module data_saparate(
input wire [79:0] fft2d_data,
output wire [36:0] real_part,
output wire [36:0] img_part
    );
    
//assign  real_part={fft2d_data[36],fft2d_data[30:0]};
//assign  img_part={fft2d_data[76],fft2d_data[70:40]}; // sign + low 31
assign real_part = fft2d_data[36:0];
assign img_part = fft2d_data[76:40];
endmodule
