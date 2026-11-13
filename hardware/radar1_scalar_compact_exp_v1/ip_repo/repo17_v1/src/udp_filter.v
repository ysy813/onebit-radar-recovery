`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/04/03 14:59:58
// Design Name: 
// Module Name: udp_filter
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module udp_filter(
        input	wire 			sclk,
		input	wire 			rst,
		input	wire 			rx_en,
		input	wire 			error_en,
		input	wire 	[7:0]	rx_data,
		input	wire 	[15:0]	statusi,
		output	reg 	[7:0]	pixels,
		output	reg 			pixels_vld
    );
    
reg      [13:0] rx_cnt;
reg 		pixel_flag;

// reg   [1:0]	rx_en_r;
// reg 		rx_en_pos;	
reg 		rx_cnt_error;	

// always @(posedge sclk or negedge rst) begin
//     if(!rst_n) begin
//         rx_en_r <= 2'b0;
//     end
//     else begin
//         rx_en_r <= {rx_en_r[0] , rx_en};
//     end
// end

// assign  rx_en_pos   =   ~rx_en_r[1] &   rx_en_r[0]  ;

always @(posedge sclk or negedge rst) begin
	if (!rst) begin
		rx_cnt_error <=1'd0;
	end
	else if (error_en) begin
		rx_cnt_error <=1'd1;
	end
	else if (!rx_en) begin
		rx_cnt_error <=1'd0;
	end
end



always @(posedge sclk or negedge rst) begin
	if (!rst) begin
		rx_cnt <=14'd0;
	end
	else if (rx_cnt_error) begin
		rx_cnt <=14'd0;
	end
	else if (rx_en == 1'b1) begin
		rx_cnt <= rx_cnt + 1'b1;
	end
	else begin
		rx_cnt <=14'd0;
	end
end

always @(posedge sclk or negedge rst) begin
	if (!rst) begin
		pixel_flag <= 1'b0;
	end
	
	else if (rx_en == 1'b1 && rx_cnt == 14'd59 && statusi > 16'd8) begin		//rx_en == 1'b1 && rx_cnt == 'd49
		pixel_flag <= 1'b1;													//statusi > 'd8 可以把短包滤掉
	end

	//else if(rx_en == 1'b1 && rx_cnt == (statusi[13:0]-5)) begin
	else if(rx_en == 1'b1 && rx_cnt == (statusi + 16'd49)) begin
		pixel_flag <= 1'b0;
	end
end

always @(posedge sclk) begin
	pixels_vld <= pixel_flag;
end

always @(posedge sclk) begin
	if (!rst) begin
		pixels <=8'd0;
	end
	else if (pixel_flag == 1'b1) begin
		pixels <= rx_data ;
	end
	else begin
		pixels <=8'd0;
	end
end
    
endmodule
