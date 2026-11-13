`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/04/07 10:01:57
// Design Name: 
// Module Name: fifoila
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


module fifoila(
input wire fifo_tready,//fifo写使能
input wire fifo_tvalid,//fifo写数据有效
input wire fifo_mtready,//fifo读使能
input wire fifo_mvalid,//fifo读数据有效，
input wire [31:0] rd_count,
output wire [127:0] probe0
    );
assign probe0 = {
   fifo_tready,
   fifo_tvalid,
   fifo_mtready,
   fifo_mvalid,
   rd_count
   

};
endmodule
