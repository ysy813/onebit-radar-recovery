// (c) Copyright 1995-2023 Xilinx, Inc. All rights reserved.
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


// IP VLNV: xilinx.com:module_ref:dvi_transmitter_top:1.0
// IP Revision: 1

(* X_CORE_INFO = "dvi_transmitter_top,Vivado 2022.1" *)
(* CHECK_LICENSE_TYPE = "hdmi_dvi_transmitter_top_0_0,dvi_transmitter_top,{}" *)
(* CORE_GENERATION_INFO = "hdmi_dvi_transmitter_top_0_0,dvi_transmitter_top,{x_ipProduct=Vivado 2022.1,x_ipVendor=xilinx.com,x_ipLibrary=module_ref,x_ipName=dvi_transmitter_top,x_ipVersion=1.0,x_ipCoreRevision=1,x_ipLanguage=VERILOG,x_ipSimLanguage=MIXED}" *)
(* IP_DEFINITION_SOURCE = "module_ref" *)
(* DowngradeIPIdentifiedWarnings = "yes" *)
module hdmi_dvi_transmitter_top_0_0 (
  pclk,
  pixel_clk_5x,
  pixel_clk_2_5x,
  reset_n,
  video_din,
  video_hsync,
  video_vsync,
  video_de,
  tmds_clk_p,
  tmds_clk_n,
  tmds_data_p,
  tmds_data_n,
  tmds_oen
);

input wire pclk;
input wire pixel_clk_5x;
input wire pixel_clk_2_5x;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME reset_n, POLARITY ACTIVE_LOW, INSERT_VIP 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 reset_n RST" *)
input wire reset_n;
input wire [23 : 0] video_din;
input wire video_hsync;
input wire video_vsync;
input wire video_de;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME tmds_clk_p, FREQ_HZ 100000000, PHASE 0.000, CLK_DOMAIN hdmi_dvi_transmitter_top_0_0_tmds_clk_p, INSERT_VIP 0, FREQ_TOLERANCE_HZ 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 tmds_clk_p CLK" *)
output wire tmds_clk_p;
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME tmds_clk_n, ASSOCIATED_RESET reset_n, FREQ_HZ 100000000, PHASE 0.000, CLK_DOMAIN hdmi_dvi_transmitter_top_0_0_tmds_clk_n, INSERT_VIP 0, FREQ_TOLERANCE_HZ 0" *)
(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 tmds_clk_n CLK" *)
output wire tmds_clk_n;
output wire [2 : 0] tmds_data_p;
output wire [2 : 0] tmds_data_n;
output wire tmds_oen;

  dvi_transmitter_top inst (
    .pclk(pclk),
    .pixel_clk_5x(pixel_clk_5x),
    .pixel_clk_2_5x(pixel_clk_2_5x),
    .reset_n(reset_n),
    .video_din(video_din),
    .video_hsync(video_hsync),
    .video_vsync(video_vsync),
    .video_de(video_de),
    .tmds_clk_p(tmds_clk_p),
    .tmds_clk_n(tmds_clk_n),
    .tmds_data_p(tmds_data_p),
    .tmds_data_n(tmds_data_n),
    .tmds_oen(tmds_oen)
  );
endmodule
