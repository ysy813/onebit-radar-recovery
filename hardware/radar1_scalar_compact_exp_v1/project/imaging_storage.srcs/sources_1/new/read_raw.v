`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/05/23 16:37:19
// Design Name: 
// Module Name: read_raw
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


module read_raw(
       input wire [12:0] rd_count,
       input wire clk,
       output wire rd_en
    );
reg rd_en1 = 0;
assign rd_en = rd_en1;
always @(posedge clk) begin
    if(rd_count >= 'd5)
      rd_en1 <= 1'b1;
end
endmodule
