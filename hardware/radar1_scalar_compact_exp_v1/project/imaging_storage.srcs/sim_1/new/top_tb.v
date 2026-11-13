`timescale 1ns / 1ps




module top_tb( );

reg clk;
reg rstn;

initial clk=0;
always #10 clk=~clk;

initial rstn=1;



 design_2_wrapper inst
   (.aclk(clk),
    .rstn(rstn)
    );
endmodule
