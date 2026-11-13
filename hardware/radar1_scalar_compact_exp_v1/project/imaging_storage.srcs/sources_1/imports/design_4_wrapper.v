//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2022.1 (win64) Build 3526262 Mon Apr 18 15:48:16 MDT 2022
//Date        : Tue May 21 19:17:47 2024
//Host        : DESKTOP-MMB8I15 running 64-bit major release  (build 9200)
//Command     : generate_target design_4_wrapper.bd
//Design      : design_4_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module design_4_wrapper
   (eth_rx_ctl,
    eth_rxc,
    eth_rxd,
    eth_tx_ctl,
    eth_txc,
    eth_txd,
    key0,
    sys_rst_n);
  input eth_rx_ctl;
  input eth_rxc;
  input [3:0]eth_rxd;
  output eth_tx_ctl;
  output eth_txc;
  output [3:0]eth_txd;
  input key0;
  input sys_rst_n;

  wire eth_rx_ctl;
  wire eth_rxc;
  wire [3:0]eth_rxd;
  wire eth_tx_ctl;
  wire eth_txc;
  wire [3:0]eth_txd;
  wire key0;
  wire sys_rst_n;

  design_4 design_4_i
       (.eth_rx_ctl(eth_rx_ctl),
        .eth_rxc(eth_rxc),
        .eth_rxd(eth_rxd),
        .eth_tx_ctl(eth_tx_ctl),
        .eth_txc(eth_txc),
        .eth_txd(eth_txd),
        .key0(key0),
        .sys_rst_n(sys_rst_n));
endmodule
