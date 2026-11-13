// (c) Copyright 1995-2024 Xilinx, Inc. All rights reserved.
// 
// This file contains confidential and proprietary information
// of Xilinx, Inc. and is protected under U.S. and
// international copyright and other intellectual property
// laws.
// 
// DISCLAIMER
// This disclaimer is not a license and does not grant any
// rights to the materials distributed herewith. Except as
// otherwise provided in a valid license issued to you by
// Xilinx, and to the maximum extent permitted by applicable
// law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
// WITH ALL FAULTS, AND XILINX HEREBY DISCLAIMS ALL WARRANTIES
// AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING
// BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
// INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and
// (2) Xilinx shall not be liable (whether in contract or tort,
// including negligence, or under any other theory of
// liability) for any loss or damage of any kind or nature
// related to, arising under or in connection with these
// materials, including for any direct, or any indirect,
// special, incidental, or consequential loss or damage
// (including loss of data, profits, goodwill, or any type of
// loss or damage suffered as a result of any action brought
// by a third party) even if such damage or loss was
// reasonably foreseeable or Xilinx had been advised of the
// possibility of the same.
// 
// CRITICAL APPLICATIONS
// Xilinx products are not designed or intended to be fail-
// safe, or for use in any application requiring fail-safe
// performance, such as life-support or safety devices or
// systems, Class III medical devices, nuclear facilities,
// applications related to the deployment of airbags, or any
// other applications that could lead to death, personal
// injury, or severe property or environmental damage
// (individually and collectively, "Critical
// Applications"). Customer assumes the sole risk and
// liability of any use of Xilinx products in Critical
// Applications, subject only to applicable laws and
// regulations governing limitations on product liability.
// 
// THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS
// PART OF THIS FILE AT ALL TIMES.
// 
// DO NOT MODIFY THIS FILE.


// IP VLNV: xilinx.com:module_ref:video_display:1.0
// IP Revision: 1

`timescale 1ns/1ps

(* IP_DEFINITION_SOURCE = "module_ref" *)
(* DowngradeIPIdentifiedWarnings = "yes" *)
module hdmi_video_display_0_0 (
  pixel_clk,
  sys_rst_n,
  cam_data_in,
  radar_data_in,
  data_req,
  pixel_xpos,
  pixel_ypos,
  pixel_data,
  data_valid,
  cam_valid,
  picture_data,
  picture_data1,
  picture_data2,
  rom_addr,
  rom_addr1,
  rom_addr2
);

(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME pixel_clk, FREQ_HZ 148500000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN hdmi_pixel_clk_1x, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 pixel_clk CLK" *)
input wire pixel_clk;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME sys_rst_n, POLARITY ACTIVE_LOW, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 sys_rst_n RST" *)
input wire sys_rst_n;
input wire [23 : 0] cam_data_in;
input wire [63 : 0] radar_data_in;
input wire data_req;
input wire [14 : 0] pixel_xpos;
input wire [14 : 0] pixel_ypos;
output wire [23 : 0] pixel_data;
output wire data_valid;
output wire cam_valid;
input wire [23 : 0] picture_data;
input wire [23 : 0] picture_data1;
input wire [23 : 0] picture_data2;
output wire [15 : 0] rom_addr;
output wire [15 : 0] rom_addr1;
output wire [15 : 0] rom_addr2;

  video_display #(
    .H_DISP(1920),
    .RAD_X_START(1),
    .RAD_Y_START(1),
    .RAD_WIDTH(512),
    .RAD_HEIGH(1024),
    .CAM_X_START(520),
    .CAM_Y_START(1),
    .CAM_WIDTH(1280),
    .CAM_HEIGH(720)
  ) inst (
    .pixel_clk(pixel_clk),
    .sys_rst_n(sys_rst_n),
    .cam_data_in(cam_data_in),
    .radar_data_in(radar_data_in),
    .data_req(data_req),
    .pixel_xpos(pixel_xpos),
    .pixel_ypos(pixel_ypos),
    .pixel_data(pixel_data),
    .data_valid(data_valid),
    .cam_valid(cam_valid),
    .picture_data(picture_data),
    .picture_data1(picture_data1),
    .picture_data2(picture_data2),
    .rom_addr(rom_addr),
    .rom_addr1(rom_addr1),
    .rom_addr2(rom_addr2)
  );
endmodule
