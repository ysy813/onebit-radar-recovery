`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/12/11 16:18:50
// Design Name: 
// Module Name: gate
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


module gate(
 input en ,
 input in ,
 output sadi,
 inout out
);
assign out = en ? in : 1'bz;
assign sadi = out;
endmodule