//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2022.1 (win64) Build 3526262 Mon Apr 18 15:48:16 MDT 2022
//Date        : Sat Apr  6 14:29:01 2024
//Host        : DESKTOP-T0BPTA8 running 64-bit major release  (build 9200)
//Command     : generate_target design_2_wrapper.bd
//Design      : design_2_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module design_2_wrapper
   (aclk,
    rstn);
  input aclk;
  input rstn;

  wire aclk;
  wire rstn;

  design_2 design_2_i
       (.aclk(aclk),
        .rstn(rstn));
endmodule
