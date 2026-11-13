//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2022.1 (win64) Build 3526262 Mon Apr 18 15:48:16 MDT 2022
//Date        : Fri Jun  7 12:17:03 2024
//Host        : DESKTOP-T0BPTA8 running 64-bit major release  (build 9200)
//Command     : generate_target design_1_wrapper.bd
//Design      : design_1_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module design_1_wrapper
   (c0_ddr4_act_n,
    c0_ddr4_adr,
    c0_ddr4_ba,
    c0_ddr4_bg,
    c0_ddr4_ck_c,
    c0_ddr4_ck_t,
    c0_ddr4_cke,
    c0_ddr4_cs_n,
    c0_ddr4_dm_n,
    c0_ddr4_dq,
    c0_ddr4_dqs_c,
    c0_ddr4_dqs_t,
    c0_ddr4_odt,
    c0_ddr4_reset_n,
    cam_data,
    cam_href,
    cam_pclk,
    cam_pwdn,
    cam_rst_n,
    cam_scl,
    cam_sda,
    cam_vsync,
    eth_rx_ctl,
    eth_rxc,
    eth_rxd,
    eth_tx_ctl,
    eth_txc,
    eth_txd,
    key0,
    sys_clk_n,
    sys_clk_p,
    sys_rst_n,
    tmds_clk_n,
    tmds_clk_p,
    tmds_data_n,
    tmds_data_p);
  output c0_ddr4_act_n;
  output [16:0]c0_ddr4_adr;
  output [1:0]c0_ddr4_ba;
  output [0:0]c0_ddr4_bg;
  output [0:0]c0_ddr4_ck_c;
  output [0:0]c0_ddr4_ck_t;
  output [0:0]c0_ddr4_cke;
  output [0:0]c0_ddr4_cs_n;
  inout [1:0]c0_ddr4_dm_n;
  inout [15:0]c0_ddr4_dq;
  inout [1:0]c0_ddr4_dqs_c;
  inout [1:0]c0_ddr4_dqs_t;
  output [0:0]c0_ddr4_odt;
  output c0_ddr4_reset_n;
  input [7:0]cam_data;
  input cam_href;
  input cam_pclk;
  output cam_pwdn;
  output cam_rst_n;
  output cam_scl;
  inout cam_sda;
  input cam_vsync;
  input eth_rx_ctl;
  input eth_rxc;
  input [3:0]eth_rxd;
  output eth_tx_ctl;
  output eth_txc;
  output [3:0]eth_txd;
  input key0;
  input sys_clk_n;
  input sys_clk_p;
  input sys_rst_n;
  output tmds_clk_n;
  output tmds_clk_p;
  output [2:0]tmds_data_n;
  output [2:0]tmds_data_p;

  wire c0_ddr4_act_n;
  wire [16:0]c0_ddr4_adr;
  wire [1:0]c0_ddr4_ba;
  wire [0:0]c0_ddr4_bg;
  wire [0:0]c0_ddr4_ck_c;
  wire [0:0]c0_ddr4_ck_t;
  wire [0:0]c0_ddr4_cke;
  wire [0:0]c0_ddr4_cs_n;
  wire [1:0]c0_ddr4_dm_n;
  wire [15:0]c0_ddr4_dq;
  wire [1:0]c0_ddr4_dqs_c;
  wire [1:0]c0_ddr4_dqs_t;
  wire [0:0]c0_ddr4_odt;
  wire c0_ddr4_reset_n;
  wire [7:0]cam_data;
  wire cam_href;
  wire cam_pclk;
  wire cam_pwdn;
  wire cam_rst_n;
  wire cam_scl;
  wire cam_sda;
  wire cam_vsync;
  wire eth_rx_ctl;
  wire eth_rxc;
  wire [3:0]eth_rxd;
  wire eth_tx_ctl;
  wire eth_txc;
  wire [3:0]eth_txd;
  wire key0;
  wire sys_clk_n;
  wire sys_clk_p;
  wire sys_rst_n;
  wire tmds_clk_n;
  wire tmds_clk_p;
  wire [2:0]tmds_data_n;
  wire [2:0]tmds_data_p;

  design_1 design_1_i
       (.c0_ddr4_act_n(c0_ddr4_act_n),
        .c0_ddr4_adr(c0_ddr4_adr),
        .c0_ddr4_ba(c0_ddr4_ba),
        .c0_ddr4_bg(c0_ddr4_bg),
        .c0_ddr4_ck_c(c0_ddr4_ck_c),
        .c0_ddr4_ck_t(c0_ddr4_ck_t),
        .c0_ddr4_cke(c0_ddr4_cke),
        .c0_ddr4_cs_n(c0_ddr4_cs_n),
        .c0_ddr4_dm_n(c0_ddr4_dm_n),
        .c0_ddr4_dq(c0_ddr4_dq),
        .c0_ddr4_dqs_c(c0_ddr4_dqs_c),
        .c0_ddr4_dqs_t(c0_ddr4_dqs_t),
        .c0_ddr4_odt(c0_ddr4_odt),
        .c0_ddr4_reset_n(c0_ddr4_reset_n),
        .cam_data(cam_data),
        .cam_href(cam_href),
        .cam_pclk(cam_pclk),
        .cam_pwdn(cam_pwdn),
        .cam_rst_n(cam_rst_n),
        .cam_scl(cam_scl),
        .cam_sda(cam_sda),
        .cam_vsync(cam_vsync),
        .eth_rx_ctl(eth_rx_ctl),
        .eth_rxc(eth_rxc),
        .eth_rxd(eth_rxd),
        .eth_tx_ctl(eth_tx_ctl),
        .eth_txc(eth_txc),
        .eth_txd(eth_txd),
        .key0(key0),
        .sys_clk_n(sys_clk_n),
        .sys_clk_p(sys_clk_p),
        .sys_rst_n(sys_rst_n),
        .tmds_clk_n(tmds_clk_n),
        .tmds_clk_p(tmds_clk_p),
        .tmds_data_n(tmds_data_n),
        .tmds_data_p(tmds_data_p));
endmodule
