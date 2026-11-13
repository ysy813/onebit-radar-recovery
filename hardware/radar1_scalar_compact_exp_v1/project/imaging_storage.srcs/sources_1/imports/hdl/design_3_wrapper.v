//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2022.1 (win64) Build 3526262 Mon Apr 18 15:48:16 MDT 2022
//Date        : Mon Apr  8 12:12:58 2024
//Host        : DESKTOP-T0BPTA8 running 64-bit major release  (build 9200)
//Command     : generate_target design_3_wrapper.bd
//Design      : design_3_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module design_3_wrapper
   (clk,
    rdata,
    read_pulse,
    rready,
    rst);
  input clk;
  input [31:0]rdata;
  input read_pulse;
  output rready;
  input rst;

  wire clk;
  wire [31:0]rdata;
  wire read_pulse;
  wire rready;
  wire rst;

  design_3 design_3_i
       (.clk(clk),
        .rdata(rdata),
        .read_pulse(read_pulse),
        .rready(rready),
        .rst(rst));
endmodule
