`timescale 1ns/1ps
// 720p display layout. The legacy power pixels are already reduced 2:1 by the DDR reader.
// No changes to the imaging power, interpolation, or saved raw I/Q data.
module video_display(
 input pixel_clk,sys_rst_n,input [23:0] cam_data_in,input [63:0] radar_data_in,
 input data_req,input [14:0] pixel_xpos,pixel_ypos,
 output reg [23:0] pixel_data,output wire data_valid,cam_valid,
 input [23:0] picture_data,picture_data1,picture_data2,
 output wire [15:0] rom_addr,rom_addr1,rom_addr2
);
 localparam X_START=218,Y_START=149,WIDTH=844,HEIGHT=422;
 wire image_window=(pixel_xpos>=X_START && pixel_xpos<X_START+WIDTH &&
                    pixel_ypos>=Y_START && pixel_ypos<Y_START+HEIGHT);
 assign data_valid=image_window;
 // No camera is attached in this radar configuration. Do not cover the radar image with its unused overlay.
 assign cam_valid=1'b0;
 assign rom_addr=0;assign rom_addr1=0;assign rom_addr2=0;
 always @(posedge pixel_clk) begin
  if(!sys_rst_n) pixel_data<=0;
  else if(image_window) pixel_data<={3{radar_data_in[31:24]}};
  else if(pixel_ypos<24) begin
   // Fixed bars distinguish a valid display scan from a black radar image.
   case(pixel_xpos/160)
    0:pixel_data<=24'hffffff;1:pixel_data<=24'hffff00;
    2:pixel_data<=24'h00ffff;3:pixel_data<=24'h00ff00;
    4:pixel_data<=24'hff00ff;5:pixel_data<=24'hff0000;
    6:pixel_data<=24'h0000ff;default:pixel_data<=24'h000000;
   endcase
  end else pixel_data<=24'h202020;
 end
endmodule
