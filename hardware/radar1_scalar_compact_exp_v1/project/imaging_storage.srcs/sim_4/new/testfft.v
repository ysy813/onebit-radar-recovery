`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/04/04 19:43:48
// Design Name: 
// Module Name: testfft
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


module testfft();
reg clk;
reg [31:0] rdata;
reg read_pulse;
wire rready;
reg rst;
initial begin
clk=0;
rst=0;
read_pulse=0;
//xid=5;
//yid=10;
end
always #5 clk=~clk;

initial begin
repeat(10)begin
    @(posedge clk);
end
rst=1;
repeat(10)begin
    @(posedge clk);
end
read_pulse=1;

@(posedge clk);
read_pulse=0;

@(posedge rready);
rdata=32'hFFE8FFD8;

end
design_3 u_des3
   (
    .clk(clk),
    .rdata(rdata),
    .read_pulse(read_pulse),
    .rready(rready),
    .rst(rst)
    );
endmodule
