module UART_Tx(
	input       clk,
	input       rst_n,
	input   wire [15:0] tx_data,
	input wire  tx_en,
	output reg  txd,
	output wire tx_finish
);

parameter S_IDLE = 5'd0;             //空闲状态
parameter S_START_L = 5'd1;          //发送低八位起始位
parameter S_BIT0_L = 5'd2;           //发送低八位数据位
parameter S_BIT1_L = 5'd3;
parameter S_BIT2_L = 5'd4;
parameter S_BIT3_L = 5'd5;
parameter S_BIT4_L = 5'd6;
parameter S_BIT5_L = 5'd7;
parameter S_BIT6_L = 5'd8;
parameter S_BIT7_L = 5'd9;
parameter S_STOP_L = 5'd10;          //发送低八位停止位

parameter S_WAIT = 5'd11;            //等待一个串口时钟周期

parameter S_START_H = 5'd12;          //发送高八位起始位
parameter S_BIT0_H = 5'd13;           //发送高八位数据位
parameter S_BIT1_H = 5'd14;
parameter S_BIT2_H = 5'd15;
parameter S_BIT3_H = 5'd16;
parameter S_BIT4_H = 5'd17;
parameter S_BIT5_H = 5'd18;
parameter S_BIT6_H = 5'd19;
parameter S_BIT7_H = 5'd20;
parameter S_STOP_H = 5'd21;          //发送高八位停止位

parameter CLK_F = 100000000;   //system clock frequency
parameter UART_BPS = 115200;    //串口波特率
localparam BPS_CNT = CLK_F/UART_BPS;  //相应波特率分频计数器

parameter cnt=60000;                    //计数器记到cnt值后串口输出该值

reg [4:0] state;
reg[15:0] bit_timer;           //用于控制波特率的计数器如果波特率是115200，每个数据位50000000/115200个时钟周期
//reg[15:0] tx_data;             //串口发送接口
reg[7:0]  tx_data_h;           //串口发送的高八位数据
reg[7:0]  tx_data_l;           //串口发送的低八位数据
reg       r_tx_finish=0;

always@(posedge clk or negedge rst_n)begin
	if(!rst_n)begin
		state <= S_IDLE;
		bit_timer <= 16'd0;
		txd <= 1'b1;
		
	end
	else begin
		case(state)
			S_IDLE:begin
				txd <= 1'b1;
				bit_timer <= 16'd0;
				//tx_data <= tx_data + 16'd1;
				if(tx_en == 1)begin
					tx_data_h <= tx_data[7:0];
					tx_data_l <= tx_data[15:8];
					//tx_data <= 0;
					state <= S_START_L;
			end
			    else 
			        state<=S_IDLE;
		end
			
			S_START_L:begin
				txd <= 1'b0;
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT0_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT0_L:begin
				//txd <= tx_data[0];
				txd <= tx_data_l[0];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT1_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT1_L:begin
				//txd <= tx_data[1];
				txd <= tx_data_l[1];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT2_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT2_L:begin
				//txd <= tx_data[2];
				txd <= tx_data_l[2];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT3_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT3_L:begin
				//txd <= tx_data[3];
				txd <= tx_data_l[3];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT4_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT4_L:begin
				//txd <= tx_data[4];
				txd <= tx_data_l[4];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT5_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT5_L:begin
				//txd <= tx_data[5];
				txd <= tx_data_l[5];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT6_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT6_L:begin
				//txd <= tx_data[6];
				txd <= tx_data_l[6];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT7_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT7_L:begin
				//txd <= tx_data[7];
				txd <= tx_data_l[7];
				if(bit_timer==BPS_CNT)begin
					state <= S_STOP_L;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_STOP_L:begin
				txd <= 1'b1;
				if(bit_timer==BPS_CNT)begin
					state <= S_START_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
//			S_WAIT:begin
//				txd <= 1'b1;
//				if(bit_timer==BPS_CNT)begin
//					state <= S_START_H;
//					bit_timer <= 16'd0;
//				end
//				else begin
//					state <= state;
//					bit_timer <= bit_timer + 16'd1;
//				end
//			end
			
			S_START_H:begin
				txd <= 1'b0;
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT0_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT0_H:begin
				//txd <= tx_data[8];
				txd <= tx_data_h[0];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT1_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT1_H:begin
				//txd <= tx_data[9];
				txd <= tx_data_h[1];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT2_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT2_H:begin
				//txd <= tx_data[10];
				txd <= tx_data_h[2];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT3_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT3_H:begin
				//txd <= tx_data[11];
				txd <= tx_data_h[3];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT4_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT4_H:begin
				//txd <= tx_data[12];
				txd <= tx_data_h[4];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT5_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT5_H:begin
				//txd <= tx_data[13];
				txd <= tx_data_h[5];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT6_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT6_H:begin
				//txd <= tx_data[14];
				txd <= tx_data_h[6];
				if(bit_timer==BPS_CNT)begin
					state <= S_BIT7_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_BIT7_H:begin
				//txd <= tx_data[15];
				txd <= tx_data_h[7];
				if(bit_timer==BPS_CNT)begin
					state <= S_STOP_H;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			S_STOP_H:begin
				txd <= 1'b1;
				if(bit_timer==BPS_CNT)begin
					state <= S_IDLE;
					bit_timer <= 16'd0;
				end
				else begin
					state <= state;
					bit_timer <= bit_timer + 16'd1;
				end
			end
			
			default: state <= S_IDLE;
		endcase
		end
	
	end

always@(posedge clk)begin
if(state==S_STOP_H && bit_timer==BPS_CNT)
    r_tx_finish<=1;
 else
    r_tx_finish<=0;
end

assign tx_finish=r_tx_finish;

endmodule

