// Bundled-data toggle handshake. Result stays stable until the next job.
module network_cdc(
 input wire fast_clk,input wire fast_rst_n,input wire slow_clk,input wire slow_rst_n,
 input wire start_fast,output reg done_fast,output wire idle_fast,
 output reg [31:0] result_fast,
 output reg start_slow,input wire done_slow,input wire idle_slow,input wire [31:0] result_slow
);
 reg request_toggle;
 (* ASYNC_REG="TRUE" *) reg [1:0] req_sync;
 reg req_seen,done_toggle;
 (* ASYNC_REG="TRUE" *) reg [1:0] done_sync;
 (* ASYNC_REG="TRUE" *) reg [1:0] idle_sync;
 reg done_seen;
 assign idle_fast=idle_sync[1];
 always @(posedge fast_clk)begin
  if(!fast_rst_n)begin request_toggle<=0;done_sync<=0;idle_sync<=0;done_seen<=0;done_fast<=0;result_fast<=0;end
  else begin
   if(start_fast)request_toggle<=~request_toggle;
   done_sync<={done_sync[0],done_toggle};idle_sync<={idle_sync[0],idle_slow};
   done_fast<=0;
   if(done_sync[1]!=done_seen)begin done_seen<=done_sync[1];done_fast<=1;result_fast<=result_slow;end
  end
 end
 always @(posedge slow_clk)begin
  if(!slow_rst_n)begin req_sync<=0;req_seen<=0;start_slow<=0;done_toggle<=0;end
  else begin
   req_sync<={req_sync[0],request_toggle};start_slow<=0;
   if(req_sync[1]!=req_seen)begin req_seen<=req_sync[1];start_slow<=1;end
   if(done_slow)done_toggle<=~done_toggle;
  end
 end
endmodule
