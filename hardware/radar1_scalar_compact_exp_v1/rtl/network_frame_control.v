`timescale 1ns/1ps
// Owns the FFT->network->interpolation frame until display handoff. Ingress
// always consumes complete frames; busy frames are intentionally skipped on
// the IMAGE branch only. The RAW storage fork is upstream and independent.
module network_frame_control #(
 parameter integer FRAME_WORDS=524288,
 parameter [31:0] WATCHDOG_CYCLES=32'd3750000000
)(
 input wire clk,input wire rst_n,
 input wire onebit_request,input wire network_request,
 input wire [31:0] s_axis_tdata,input wire s_axis_tvalid,output wire s_axis_tready,
 output wire [31:0] m_axis_tdata,output wire m_axis_tvalid,input wire m_axis_tready,
 input wire fft_done,input wire interp_done,
 output reg net_start,input wire net_done,input wire net_idle,
 input wire [31:0] suppressed,
 output reg interp_start,
 output reg [31:0] admitted,output reg [31:0] skipped,
 output wire [31:0] status,output reg [31:0] last_cycles,
 output reg [31:0] last_suppressed
);
 reg [18:0] pos;
 reg selected,decision_valid,accept_frame,busy,network_locked;
 reg [2:0] stage;
 reg [31:0] cycles;
 reg [15:0] completed;
 reg timeout_fault,unexpected_done;
 wire admit_now=!busy;
 wire take_frame=decision_valid?accept_frame:admit_now;
 wire transfer=s_axis_tvalid && s_axis_tready;
 assign s_axis_tready=rst_n && (!take_frame || m_axis_tready);
 assign m_axis_tdata=s_axis_tdata;
 assign m_axis_tvalid=rst_n && s_axis_tvalid && take_frame;
 assign status={completed,8'h71,2'b0,unexpected_done,timeout_fault,selected,stage!=0,busy,net_idle};
 always @(posedge clk)begin
  if(!rst_n)begin
   pos<=0;selected<=0;decision_valid<=0;accept_frame<=0;busy<=0;network_locked<=0;
   stage<=0;cycles<=0;completed<=0;timeout_fault<=0;unexpected_done<=0;
   net_start<=0;interp_start<=0;admitted<=0;skipped<=0;last_cycles<=0;last_suppressed<=0;
  end else begin
   net_start<=0;interp_start<=0;
   if(transfer)begin
    if(!decision_valid)begin
     decision_valid<=1;accept_frame<=admit_now;
     if(admit_now)begin busy<=1;admitted<=admitted+1;end
     else skipped<=skipped+1;
     if(!network_locked)begin selected<=onebit_request && network_request;network_locked<=1;end
    end
    if(pos==FRAME_WORDS-1)begin pos<=0;decision_valid<=0;end
    else pos<=pos+1;
   end
   case(stage)
    0: if(fft_done)begin
     if(!busy)unexpected_done<=1;
     if(selected)begin net_start<=1;stage<=1;cycles<=0;end
     else begin interp_start<=1;stage<=2;end
    end
    1: begin
     cycles<=cycles+1;
     if(net_done)begin
      last_cycles<=cycles+1;last_suppressed<=suppressed;
      completed<=completed+1;interp_start<=1;stage<=2;
     end else if(cycles==WATCHDOG_CYCLES-1)begin timeout_fault<=1;stage<=3;end
    end
    2: if(interp_done)begin busy<=0;stage<=0;end
    3: begin end // fail closed: a timed-out partially modified frame is not displayed
    default: stage<=3;
   endcase
  end
 end
endmodule
