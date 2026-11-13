//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2022.1 (win64) Build 3526262 Mon Apr 18 15:48:16 MDT 2022
//Date        : Fri Mar  1 19:10:29 2024
//Host        : DESKTOP-MMB8I15 running 64-bit major release  (build 9200)
//Command     : generate_target hdmi.bd
//Design      : hdmi
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CORE_GENERATION_INFO = "hdmi,IP_Integrator,{x_ipVendor=xilinx.com,x_ipLibrary=BlockDiagram,x_ipName=hdmi,x_ipVersion=1.00.a,x_ipLanguage=VERILOG,numBlks=5,numReposBlks=5,numNonXlnxBlks=0,numHierBlks=0,maxHierDepth=0,numSysgenBlks=0,numHlsBlks=0,numHdlrefBlks=3,numPkgbdBlks=0,bdsource=USER,synth_mode=Global}" *) (* HW_HANDOFF = "hdmi.hwdef" *) 
module hdmi
   (cam_data_in,
    cam_fifo_en,
    data_in,
    picture_data,
    picture_data1,
    picture_data2,
    pixel_clk_1x,
    pixel_clk_2_5x,
    pixel_clk_5x,
    rfifo_rd_en,
    rom_addr,
    rom_addr1,
    rom_addr2,
    rstn,
    tmds_clk_n,
    tmds_clk_p,
    tmds_data_n,
    tmds_data_p,
    vedio_vs);
  input [23:0]cam_data_in;
  output [0:0]cam_fifo_en;
  input [63:0]data_in;
  input [23:0]picture_data;
  input [23:0]picture_data1;
  input [23:0]picture_data2;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.PIXEL_CLK_1X CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.PIXEL_CLK_1X, CLK_DOMAIN hdmi_pixel_clk_1x, FREQ_HZ 74250000, FREQ_TOLERANCE_HZ 0, INSERT_VIP 0, PHASE 0.0" *) input pixel_clk_1x;
  input pixel_clk_2_5x;
  input pixel_clk_5x;
  output [0:0]rfifo_rd_en;
  output [15:0]rom_addr;
  output [15:0]rom_addr1;
  output [15:0]rom_addr2;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 RST.RSTN RST" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME RST.RSTN, INSERT_VIP 0, POLARITY ACTIVE_LOW" *) input rstn;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.TMDS_CLK_N CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.TMDS_CLK_N, CLK_DOMAIN hdmi_dvi_transmitter_top_0_0_tmds_clk_n, FREQ_HZ 100000000, FREQ_TOLERANCE_HZ 0, INSERT_VIP 0, PHASE 0.000" *) output tmds_clk_n;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 CLK.TMDS_CLK_P CLK" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME CLK.TMDS_CLK_P, CLK_DOMAIN hdmi_dvi_transmitter_top_0_0_tmds_clk_p, FREQ_HZ 100000000, FREQ_TOLERANCE_HZ 0, INSERT_VIP 0, PHASE 0.000" *) output tmds_clk_p;
  output [2:0]tmds_data_n;
  output [2:0]tmds_data_p;
  output vedio_vs;

  wire [23:0]cam_data_in_0_1;
  wire clk_wiz_0_clk_1;
  wire [63:0]data_in_0_1;
  wire dvi_transmitter_top_0_tmds_clk_n;
  wire dvi_transmitter_top_0_tmds_clk_p;
  wire [2:0]dvi_transmitter_top_0_tmds_data_n;
  wire [2:0]dvi_transmitter_top_0_tmds_data_p;
  wire [23:0]picture_data1_0_1;
  wire [23:0]picture_data2_0_1;
  wire [23:0]picture_data_0_1;
  wire pixel_clk_2_5x_0_1;
  wire pixel_clk_5x_0_1;
  wire reset_n_0_1;
  wire [0:0]util_vector_logic_0_Res;
  wire [0:0]util_vector_logic_1_Res;
  wire video_display_0_cam_valid;
  wire video_display_0_data_valid;
  wire [23:0]video_display_0_pixel_data;
  wire [15:0]video_display_0_rom_addr;
  wire [15:0]video_display_0_rom_addr1;
  wire [15:0]video_display_0_rom_addr2;
  wire video_driver_0_data_req;
  wire [14:0]video_driver_0_pixel_xpos;
  wire [14:0]video_driver_0_pixel_ypos;
  wire video_driver_0_video_de;
  wire video_driver_0_video_hs;
  wire [23:0]video_driver_0_video_rgb;
  wire video_driver_0_video_vs;

  assign cam_data_in_0_1 = cam_data_in[23:0];
  assign cam_fifo_en[0] = util_vector_logic_1_Res;
  assign clk_wiz_0_clk_1 = pixel_clk_1x;
  assign data_in_0_1 = data_in[63:0];
  assign picture_data1_0_1 = picture_data1[23:0];
  assign picture_data2_0_1 = picture_data2[23:0];
  assign picture_data_0_1 = picture_data[23:0];
  assign pixel_clk_2_5x_0_1 = pixel_clk_2_5x;
  assign pixel_clk_5x_0_1 = pixel_clk_5x;
  assign reset_n_0_1 = rstn;
  assign rfifo_rd_en[0] = util_vector_logic_0_Res;
  assign rom_addr[15:0] = video_display_0_rom_addr;
  assign rom_addr1[15:0] = video_display_0_rom_addr1;
  assign rom_addr2[15:0] = video_display_0_rom_addr2;
  assign tmds_clk_n = dvi_transmitter_top_0_tmds_clk_n;
  assign tmds_clk_p = dvi_transmitter_top_0_tmds_clk_p;
  assign tmds_data_n[2:0] = dvi_transmitter_top_0_tmds_data_n;
  assign tmds_data_p[2:0] = dvi_transmitter_top_0_tmds_data_p;
  assign vedio_vs = video_driver_0_video_vs;
  hdmi_dvi_transmitter_top_0_0 dvi_transmitter_top_0
       (.pclk(clk_wiz_0_clk_1),
        .pixel_clk_2_5x(pixel_clk_2_5x_0_1),
        .pixel_clk_5x(pixel_clk_5x_0_1),
        .reset_n(reset_n_0_1),
        .tmds_clk_n(dvi_transmitter_top_0_tmds_clk_n),
        .tmds_clk_p(dvi_transmitter_top_0_tmds_clk_p),
        .tmds_data_n(dvi_transmitter_top_0_tmds_data_n),
        .tmds_data_p(dvi_transmitter_top_0_tmds_data_p),
        .video_de(video_driver_0_video_de),
        .video_din(video_driver_0_video_rgb),
        .video_hsync(video_driver_0_video_hs),
        .video_vsync(video_driver_0_video_vs));
  hdmi_util_vector_logic_0_0 util_vector_logic_0
       (.Op1(video_driver_0_data_req),
        .Op2(video_display_0_data_valid),
        .Res(util_vector_logic_0_Res));
  hdmi_util_vector_logic_0_1 util_vector_logic_1
       (.Op1(video_driver_0_data_req),
        .Op2(video_display_0_cam_valid),
        .Res(util_vector_logic_1_Res));
  hdmi_video_display_0_0 video_display_0
       (.cam_data_in(cam_data_in_0_1),
        .cam_valid(video_display_0_cam_valid),
        .data_req(video_driver_0_data_req),
        .data_valid(video_display_0_data_valid),
        .picture_data(picture_data_0_1),
        .picture_data1(picture_data1_0_1),
        .picture_data2(picture_data2_0_1),
        .pixel_clk(clk_wiz_0_clk_1),
        .pixel_data(video_display_0_pixel_data),
        .pixel_xpos(video_driver_0_pixel_xpos),
        .pixel_ypos(video_driver_0_pixel_ypos),
        .radar_data_in(data_in_0_1),
        .rom_addr(video_display_0_rom_addr),
        .rom_addr1(video_display_0_rom_addr1),
        .rom_addr2(video_display_0_rom_addr2),
        .sys_rst_n(reset_n_0_1));
  hdmi_video_driver_0_0 video_driver_0
       (.data_req(video_driver_0_data_req),
        .pixel_clk(clk_wiz_0_clk_1),
        .pixel_data(video_display_0_pixel_data),
        .pixel_xpos(video_driver_0_pixel_xpos),
        .pixel_ypos(video_driver_0_pixel_ypos),
        .sys_rst_n(reset_n_0_1),
        .video_de(video_driver_0_video_de),
        .video_hs(video_driver_0_video_hs),
        .video_rgb(video_driver_0_video_rgb),
        .video_vs(video_driver_0_video_vs));
endmodule
