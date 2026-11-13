module signal_delay # 
 ( 
  parameter M = 1, // 设置数据宽度
  parameter N = 4 // 设置延迟时钟周期
 ) 
 ( 
  input clk, // 时钟信号
  input  data_in, // 输入数据
  output data_out // 输出数据
 ); 
reg delay0;
reg delay1;
reg delay2;
reg delay3;
reg delay4;
reg delay5;
reg delay6;
reg delay7;
reg delay8;
reg delay9;
reg delay10;
reg delay11;
always@(posedge clk)begin
    delay0<=data_in;
    delay1<=delay0;
    delay2<=delay1;
    delay3<=delay2;
    delay4<=delay3;
    delay5<=delay4;
    delay6<=delay5;
    delay7<=delay6;
    delay8<=delay7;
    delay9<=delay8;
    delay10<=delay9;
 
end

assign data_out=delay10;
endmodule