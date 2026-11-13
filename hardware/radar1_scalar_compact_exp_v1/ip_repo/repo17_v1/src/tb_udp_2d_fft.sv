`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2023/05/12 00:54:44
// Design Name: 
// Module Name: tb_udp_2d_fft
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


module tb_udp_2d_fft(

    );


`define CLK_PERIORD_100M		    10		//???????????20ns???50MHz
`define CLK_PERIORD_125M		8		//???????????8ns???125MHz

reg         clk_p;
reg         clk_n;
// wire        clk_250m;
reg         rst_n           =1                  ;

reg         key             =1;

reg         eth_rxc;
wire        eth_rxc_delay                       ;//eth_rxc????бк?2ns
reg         eth_rx_ctl;
reg  [3:0]  eth_rxd;

reg  [320:0]  str                               ;

wire        eth_txc;
wire        eth_tx_ctl;
wire [3:0]  eth_txd;
// wire        eth_rst_n;

wire [1:0]  led     ;

wire        fft_tready_s    ;
assign      fft_tready_s  =  rst_n ? 1'b1 : 1'b0 ;


localparam UDP_PACK_NUM   = 721                            ;//181 6

//reg signed [15:0] Time_data_I_re[255:0];//???????
reg   signed [7:0]    udp_head[49:0];
reg   signed [7:0]    udp_crc[3:0];
reg   signed [7:0]    arp[71:0];
//reg    [7:0]    udp_data[0:1465];
reg [0:UDP_PACK_NUM-1] [0:732] [15: 0] udp_data              ;

reg   signed [7:0]    udp_1[99:0];

reg             arp_ctrl;
reg             udp_before;
reg             udp_ctrl;
reg             udp_ctrl_1;
reg             udp_ctrl_2;
reg             zhunbei;
reg             udp_end;           
// reg             udp_ctrl_v1;
// reg             udp_ctrl_v1_1;
// reg             udp_ctrl_v1_2;
// reg             zhunbei_v1;
// reg             udp_ctrl_v2;
// reg             udp_ctrl_v2_1;
// reg             udp_ctrl_v2_2;

// wire        [15:0]  ch0_re_2d   ;
// wire        [15:0]  ch0_im_2d   ;
// wire        [15:0]  ch0_abs_2d  ;

// wire           m_fft_tvalid_2d  ;
// reg            m_fft_tvalid_2d_d1  ;
// reg            m_fft_tvalid_2d_d2  ;
// reg            m_fft_tvalid_2d_d3  ;

// always @(posedge clk_250m or negedge rst_n) begin   //delay 1 clock
//     if(!rst_n)
//         m_fft_tvalid_2d_d1 <= 1'b0;
//     else
//         m_fft_tvalid_2d_d1 <= m_fft_tvalid_2d;
// end

// always @(posedge clk_250m or negedge rst_n) begin   //delay 2 clock
//     if(!rst_n)
//         m_fft_tvalid_2d_d2 <= 1'b0;
//     else
//         m_fft_tvalid_2d_d2 <= m_fft_tvalid_2d_d1;
// end

// always @(posedge clk_250m or negedge rst_n) begin   //delay 3 clock
//     if(!rst_n)
//         m_fft_tvalid_2d_d3 <= 1'b0;
//     else
//         m_fft_tvalid_2d_d3 <= m_fft_tvalid_2d_d2;
// end

initial begin
    clk_p = 1'b1;
    clk_n = ~clk_p;
    eth_rxc = 1'b1;
    //eth_rxc_delay = 1'b1  ;
    //rst_n = 1'b0;
    eth_rx_ctl = 1'b0;
    $readmemb("D:/research/1_Verilog_100T/302_udp_fifo_fft_v2/03data/udp_headV2.txt",udp_head);
    $readmemb("D:/research/1_Verilog_100T/302_udp_fifo_fft_v2/03data/arpV2.txt",arp);
    $readmemb("D:/research/1_Verilog_100T/302_udp_fifo_fft_v2/03data/udp_crcV2.txt",udp_crc);
    //$readmemb("D:/research/1_Verilog_100T/302_udp_fifo_fft_v2/03data/table_256x4.bin",udp_data,0,1465);
    $readmemb("D:/research/1_Verilog_100T/302_udp_fifo_fft_v1/02data/udpV2.txt",udp_1);
end

/*------------------------------------*/
/*   prepare for data                 */
/*------------------------------------*/
integer       fd1, err, read_code               ;

initial begin
    //fd1 = $fopen("D:/research/1_Verilog_100T/302_udp_fifo_fft_v5/03data/table_256x4.bin", "rb");
    fd1 = $fopen("D:/research/1_Verilog_100T/303_udp_fifo_2d_fft_v4/03data/table_256x4.bin", "rb");  
    err = $ferror(fd1, str);
    $display("Error number is: %h.", err );  //0
    $display("Error info is: %s.", str );    //0
    if( !err)begin
        read_code = $fread(udp_data, fd1);      //return the readed num of bytes
        $display("Read code is :%d.", read_code);
    end
    $fclose(fd1);
end

//??????
always #(`CLK_PERIORD_100M/2)    clk_p       = ~clk_p;        //50MHZ???
always #(`CLK_PERIORD_100M/2)    clk_n       = ~clk_n;

always #(`CLK_PERIORD_125M/2) eth_rxc     = ~eth_rxc;        //125MHZ???
assign #2                   eth_rxc_delay = eth_rxc;   //delay 2ns      ?????бо???????????????????бк?


initial begin
    //#(`CLK_PERIORD_50M * 50);
    #(`CLK_PERIORD_100M * 4);
    rst_n = 1'b0;
    #(`CLK_PERIORD_100M * 4);
    rst_n = 1'b1;
    
end 


integer p;//???????? 
initial begin 
    @(posedge rst_n);
    
    @(posedge eth_rxc);
    for (p = 0; p < 72; p = p + 1) begin
        @(posedge eth_rxc);
        eth_rxd = 4'b1101;
        
        @(negedge eth_rxc);
        eth_rxd = 4'b1101;
           
        if(p == 71)
             arp_ctrl   = 1'b1;		
    end
end


integer i;//???????? 
initial begin 
    @(posedge arp_ctrl);
    // @(posedge rst_n);
    
    // @(posedge eth_rxc);
    for (i = 0; i < 72; i = i + 1) begin
        @(posedge eth_rxc);
        eth_rxd = arp[i][3:0];
        
        @(negedge eth_rxc);
        eth_rxd = arp[i][7:4];
        
        if(i == 71)
             udp_before   = 1'b1;		
    end
end


integer p1;//???????? 
initial begin 
    @(posedge udp_before);
    for (p1 = 0; p1 < 72; p1 = p1 + 1) begin
        @(posedge eth_rxc);
        eth_rxd = 4'b1101;
        
        @(negedge eth_rxc);
        eth_rxd = 4'b1101;
        
        
        if(p1 == 71)
             udp_ctrl   = 1'b1;
        else if(i == 72)
            i = 73;
    end
end

//integer cnt_32;
integer cnt;
integer j,k,m,n;
initial begin 
    @(posedge udp_ctrl);
    //for (cnt_32 = 0; cnt_32 < 32; cnt_32 = cnt_32 + 1) begin
    for (cnt = 0; cnt < UDP_PACK_NUM; cnt = cnt + 1) begin  //cnt < 6
        for (j = 0; j < 50; j = j + 1) begin
            //@(posedge eth_rxc);
            @(posedge eth_rxc);
            eth_rxd = udp_head[j][3:0];
            
            @(negedge eth_rxc);
            eth_rxd = udp_head[j][7:4];
            

            if(j == 49) begin
                udp_ctrl_1   = 1'b1;
            end
        end

        if(udp_ctrl_1  == 1'b1) begin
            
            udp_ctrl_1   = 1'b0;
            
            for (k = 0; k < 733; k = k + 1) begin
            //@(posedge eth_rxc);
                @(posedge eth_rxc);
                eth_rxd = udp_data[cnt][k][11:8];
                
                @(negedge eth_rxc);
                eth_rxd = udp_data[cnt][k][15:12];
                
                @(posedge eth_rxc);
                eth_rxd = udp_data[cnt][k][3:0];
                
                @(negedge eth_rxc);
                eth_rxd = udp_data[cnt][k][7:4];
                
                
                if(k == 732) begin
                    udp_ctrl_2   = 1'b1;
                end

            end
        end

        if(udp_ctrl_2  == 1'b1) begin
            
            udp_ctrl_2   = 1'b0;
            
            for (m = 0; m < 4; m = m + 1) begin
                @(posedge eth_rxc);
                eth_rxd = udp_crc[m][3:0];
                
                @(negedge eth_rxc);
                eth_rxd = udp_crc[m][7:4];
                

                if(m == 3) begin
                    zhunbei   = 1'b1;
                end

            end
        end

        if(zhunbei  == 1'b1) begin
            
            zhunbei   = 1'b0;
            
            for (n = 0; n < 12; n = n + 1) begin
                @(posedge eth_rxc);
                eth_rxd = 4'b1101;
                
                @(negedge eth_rxc);
                eth_rxd = 4'b1101;
                

                if(m == 4) begin
                    m = 0;
                end

            end
        end
        
        //????????100???
        // if(cnt == 5) begin
        //     //@(negedge eth_tx_ctl);
        //     #(`CLK_PERIORD_100M * 1400);
        //     key =  1'b0;
        //     #(`CLK_PERIORD_100M * 400);
        //     key =  1'b1;
        //     #(`CLK_PERIORD_100M * 1400);
        //     key =  1'b0;
        //     #(`CLK_PERIORD_100M * 400);
        //     key =  1'b1;

        //     udp_end =   1'b1;

        // end
        
    end
    //end
end


integer q,qq;//?????бу???иж??
initial begin 
    @(posedge udp_end);
    
    @(posedge eth_rxc);
    for(qq = 0; qq < 100; qq = qq + 1) begin        //???100??????udp??бн??????ии??fft????????бы??????
    //#(`CLK_PERIORD_125M*50);
        for (q = 0; q < 100; q = q + 1) begin
            @(posedge eth_rxc);
            eth_rxd = udp_1[q][3:0];
            
            @(negedge eth_rxc);
            eth_rxd = udp_1[q][7:4];
            

            //@(posedge eth_rxc);
        end
    end
end


always@(*) begin
    
    if(i == 0 || j == 0 || q == 9) begin
        @(posedge eth_rxc);
        eth_rx_ctl = 1'b1;
    end
    else if(i == 72 || m == 4 || q == 81) begin
        @(posedge eth_rxc);
        eth_rx_ctl = 1'b0;
    end
    
end


// integer re_file ;
// integer im_file ;


// initial re_file = $fopen("D:/research/fft_2d_256_64/2d_fft_data/ch0_re_2d.txt");
// always @(posedge clk_250m) begin 
//     if(m_fft_tvalid_2d_d2) begin
//         $fdisplay(re_file,"%d",ch0_re_2d);//???
//     end
// end


// initial im_file = $fopen("D:/research/fft_2d_256_64/2d_fft_data/ch0_im_2d.txt");
// always @(posedge clk_250m) begin
//     if(m_fft_tvalid_2d_d2) begin
//         $fdisplay(im_file,"%d",ch0_im_2d);//???
//     end
// end


// integer re_file_w ;
// integer im_file_w ;


// initial re_file_w = $fopen("D:/research/fft_2d_256_64/2d_fft_data/ch0_re_2d_w.txt");
// always @(posedge clk_250m) begin 
//     $fdisplay(re_file_w,"%d",ch0_re_2d);//???
// end


// initial im_file_w = $fopen("D:/research/fft_2d_256_64/2d_fft_data/ch0_im_2d_w.txt");
// always @(posedge clk_250m) begin
//     $fdisplay(im_file_w,"%d",ch0_im_2d);//???
// end

// integer abs_file  ;
// integer abs_file_w  ;
// integer b_abs_file  ;
// integer b_abs_file_w  ;
// integer b8_abs_file  ;
// integer b8_abs_file_w  ;
// integer h_abs_file  ;
// integer h_abs_file_w  ;

// initial abs_file = $fopen("D:/research/fft_2d_256_64/2d_fft_data/ch0_abs_2d.txt");
// always @(posedge clk_250m) begin
//     if(m_fft_tvalid_2d_d3) begin
//         $fdisplay(abs_file,"%d",ch0_abs_2d);//???
//     end
// end

// initial abs_file_w = $fopen("D:/research/fft_2d_256_64/2d_fft_data/ch0_abs_2d_w.txt");
// always @(posedge clk_250m) begin
//     $fdisplay(abs_file_w,"%d",ch0_abs_2d);//???
// end

// initial b_abs_file = $fopen("D:/research/fft_2d_256_64/2d_fft_data/b_ch0_abs_2d.txt");
// always @(posedge clk_250m) begin
//     if(m_fft_tvalid_2d_d3) begin
//         $fdisplay(b_abs_file,"%b",ch0_abs_2d);//???
//     end
// end

// initial b_abs_file_w = $fopen("D:/research/fft_2d_256_64/2d_fft_data/b_ch0_abs_2d_w.txt");
// always @(posedge clk_250m) begin
//     $fdisplay(b_abs_file_w,"%b",ch0_abs_2d);//???
// end

// initial b8_abs_file = $fopen("D:/research/fft_2d_256_64/2d_fft_data/b8_ch0_abs_2d.txt");
// always @(posedge clk_250m) begin
//     if(m_fft_tvalid_2d_d3) begin
//         $fdisplay(b8_abs_file,"%b",ch0_abs_2d[26:19]);//???
//     end
// end

// initial b8_abs_file_w = $fopen("D:/research/fft_2d_256_64/2d_fft_data/b8_ch0_abs_2d_w.txt");
// always @(posedge clk_250m) begin
//     $fdisplay(b8_abs_file_w,"%b",ch0_abs_2d[26:19]);//???
// end

// initial h_abs_file = $fopen("D:/research/fft_2d_256_64/2d_fft_data/h_ch0_abs_2d.txt");
// always @(posedge clk_250m) begin
//     if(m_fft_tvalid_2d_d3) begin
//         $fdisplay(h_abs_file,"%h",ch0_abs_2d);//???
//     end
// end

// initial h_abs_file_w = $fopen("D:/research/fft_2d_256_64/2d_fft_data/h_ch0_abs_2d_w.txt");
// always @(posedge clk_250m) begin
//     $fdisplay(h_abs_file_w,"%h",ch0_abs_2d);//???
// end


eth_udp_loop U_eth_udp_loop(
    .sys_clk_p      (clk_p),
    .sys_clk_n      (clk_n),
    .sys_rst_n      (rst_n),

    .key0            (key),
    
    .eth_rxc        (eth_rxc_delay),
    .eth_rx_ctl     (eth_rx_ctl),
    .eth_rxd        (eth_rxd),

    .eth_txc        (eth_txc),
    .eth_tx_ctl     (eth_tx_ctl),
    .eth_txd        (eth_txd),
    //.eth_rst_n      (eth_rst_n),
    .led            (led),
    // .ch0_abs_2d     (ch0_abs_2d),
    // .ch0_re_2d      (ch0_re_2d),
    // .ch0_im_2d      (ch0_im_2d),
    // .clk_250m       (clk_250m )

    // .m_fft_tvalid_2d(m_fft_tvalid_2d)
    
    .fft_tready_s    (fft_tready_s)
);


endmodule
