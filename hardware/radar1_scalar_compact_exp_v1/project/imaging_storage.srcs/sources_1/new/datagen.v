
module datagen(
input wire clk,
input wire axis_ready,
output wire [31:0] data,
output reg axis_valid
    );
    
reg [31:0] cnt=0;

always@(posedge clk)
    if(cnt==6000-1)
        cnt<=0;
    else
        cnt<=cnt+1;

always@(posedge clk)
    if(cnt==1025)
        axis_valid<=0;
    else if(cnt==1 && axis_ready==1)
        axis_valid<=1;
 
 
assign data=cnt;
    

endmodule
