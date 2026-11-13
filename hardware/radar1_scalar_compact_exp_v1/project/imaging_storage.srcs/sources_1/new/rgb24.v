`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/12/11 16:57:14
// Design Name: 
// Module Name: rgb24
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


module rgb24(
    input  [15:0]datain,
    output [23:0]dataout
    );
assign dataout = {datain[15:11],3'b000,datain[10:5],2'b00,datain[4:0],3'b000};
endmodule
