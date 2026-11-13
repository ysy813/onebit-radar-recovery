// -----------------------------------------------------------------------------
// Copyright (c) 2014-2019 All rights reserved
// -----------------------------------------------------------------------------
// Author : Youkaiyuan  v3eduyky@126.com
// wechat : 15921999232
// File   : bit8to128.v
// Create : 2019-10-06 16:35:47
// Editor : sublime text3, tab size (4)
// -----------------------------------------------------------------------------
module bit8to128(
	input	wire 				clk,
	input	wire 				clk_m,
	input	wire 				rst_n,
	input	wire 				wr_vld,
	input	wire 		[7:0]	wr_data,
	input	wire				re_tready,
	output	wire				re_tvalid,
	output	wire 		[127:0]	re_data,
	output	wire				re_tlast
	);

// ------ fifo wire--------

reg			[8:0]		s_axis_tvalid_cnt;

reg						s_axis_tvalid;
wire					s_axis_tready;
reg			[127:0]		s_axis_tdata;
wire					s_axis_tlast;		

wire					m_axis_tvalid;
//reg						m_axis_tready;
//wire		[127:0]		re_data;
wire					m_axis_tlast;
// -----------------------

assign	m_axis_tready	=	re_tready;
assign	re_tvalid	=	m_axis_tvalid;
assign	re_tlast	=	m_axis_tlast;

// ---------- 8 to 16（按原来顺序�?	16 to 128(fifo，排不了顺序)  + native to axi       不行�?
// ---------- 8 to 16（按原来顺序�?	16 to 128(手动排顺�?) + native to axi + fifo128to128        麻烦



// ---------- 8 to 128 （手动排顺序�? --
reg 		[3:0]		i;
reg			[127:0]		wr_data_128;
reg					s_axis_tdata_vld;
always @(posedge clk or negedge rst_n) begin
	if(!rst_n) begin
		wr_data_128 <= 128'd0;
		//s_axis_tdata <= 128'd0;
		i	<=	4'd0;
		s_axis_tdata_vld <= 1'b0;
	end
	else if(wr_vld) begin
		s_axis_tdata_vld <= 1'b0;
		case (i)										//big	大端模式  1 0		9 8		3 2		11 10		5 4		13 12		7 6		15 14
														//small 小端模式  0 1		8 9		2 3		10 11		4 5		12 13		6 7		14 15

			0:	wr_data_128[ 7: 0]		<=	wr_data;	//实部0
			1:	wr_data_128[15: 8]		<=	wr_data;

			8:	wr_data_128[23:16]		<=	wr_data;	//虚部0
			9:	wr_data_128[31:24]		<=	wr_data;

			2:	wr_data_128[39:32]		<=	wr_data;	//实部1
			3:	wr_data_128[47:40]		<=	wr_data;

			10:	wr_data_128[55:48]		<=	wr_data;	//虚部1
			11:	wr_data_128[63:56]		<=	wr_data;

			4:	wr_data_128[71:64]		<=	wr_data;	//实部2
			5:	wr_data_128[79:72]		<=	wr_data;

			12:	wr_data_128[87:80]		<=	wr_data;	//虚部2
			13:	wr_data_128[95:88]		<=	wr_data;

			6:	wr_data_128[103: 96]	<=	wr_data;	//实部3
			7:	wr_data_128[111:104]	<=	wr_data;

			14:	begin 
				wr_data_128[119:112]	<=	wr_data;	//虚部3
				//s_axis_tdata_vld 		<= 1'b1;
			end
			15:	begin 
				wr_data_128[127:120]	<=	wr_data;
				s_axis_tdata_vld 		<= 1'b1;	//fang zai 15
			end
			
			default : 		;
		endcase
		i = i + 1'b1;
	end
	else	
		s_axis_tdata_vld <= 1'b0;	
end

// -------------- fifo 128 to 128
//reg				s_axis_tdata_vld;
always @(posedge clk or negedge rst_n) begin
	if(!rst_n) begin
		s_axis_tdata <= 128'd0;
		s_axis_tvalid <= 1'b0;
		
	end
	else if(s_axis_tdata_vld == 1'b1) begin
		s_axis_tdata <= wr_data_128;
		s_axis_tvalid <= 1'b1;
	end
	else
		s_axis_tvalid <= 1'b0;
end

always @(posedge clk or negedge rst_n) begin
	if(!rst_n) begin
		s_axis_tvalid_cnt <= 9'd0;
		
	end
	else if(s_axis_tdata_vld == 1'b1) begin
		s_axis_tvalid_cnt <= s_axis_tvalid_cnt + 1'b1;
	end
	else if(s_axis_tvalid_cnt == 9'd256)
		s_axis_tvalid_cnt <= 9'd0;
end

assign	s_axis_tlast  =  (s_axis_tvalid_cnt == 9'd256) ? 1'b1 : 1'b0 ;

// always @(posedge clk or negedge rst_n) begin
// 	if(!rst_n) begin
// 		s_axis_tlast <= 1'b0;
// 	end
// 	else if(s_axis_tdata_vld == 1'b1 && wr_vld == 1'b0) begin
// 		s_axis_tlast <= 1'b0;//1'b1;
// 	end
// 	else
// 		s_axis_tlast <= 1'b0;
// end



axis_data_fifo_0 u_axis_data_fifo (
  .s_axis_aresetn(rst_n),  // input wire s_axis_aresetn
  .s_axis_aclk(clk),        // input wire s_axis_aclk

  .s_axis_tvalid(s_axis_tvalid),    // input wire s_axis_tvalid
  .s_axis_tready(s_axis_tready),    // output wire s_axis_tready
  .s_axis_tdata(s_axis_tdata),      // input wire [127 : 0] s_axis_tdata
  .s_axis_tlast(s_axis_tlast),      // input wire s_axis_tlast

  .m_axis_aclk(clk_m),        // input wire m_axis_aclk
  .m_axis_tvalid(m_axis_tvalid),    // output wire m_axis_tvalid
  .m_axis_tready(m_axis_tready),    // input wire m_axis_tready
  .m_axis_tdata(re_data),      // output wire [127 : 0] m_axis_tdata
  .m_axis_tlast(m_axis_tlast)      // output wire m_axis_tlast

); 





// INST_TAG_END ------ End INSTANTIATION Template ---------


endmodule