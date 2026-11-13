#时钟周期约束
# create_clock -name sys_clk_p -period 10 [get_ports sys_clk_p]

create_clock -period 8.000 -name eth_rxc [get_ports eth_rxc]

#复位
set_property IOSTANDARD LVCMOS33 [get_ports sys_rst_n]
set_property PACKAGE_PIN AH11 [get_ports sys_rst_n]

#时钟
# set_property IOSTANDARD DIFF_HSTL_I_12 [get_ports sys_clk_p]
# set_property IOSTANDARD DIFF_HSTL_I_12 [get_ports sys_clk_n]
# set_property PACKAGE_PIN AE5 [get_ports sys_clk_p]
# set_property PACKAGE_PIN AF5 [get_ports sys_clk_n]

# 网口
set_property IOSTANDARD LVCMOS18 [get_ports {eth_rxd[3]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_rxd[2]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_rxd[1]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_rxd[0]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_txd[3]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_txd[2]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_txd[1]}]
set_property IOSTANDARD LVCMOS18 [get_ports {eth_txd[0]}]
set_property IOSTANDARD LVCMOS18 [get_ports eth_rx_ctl]
set_property IOSTANDARD LVCMOS18 [get_ports eth_rxc]
set_property IOSTANDARD LVCMOS18 [get_ports eth_tx_ctl]
set_property IOSTANDARD LVCMOS18 [get_ports eth_txc]
set_property PACKAGE_PIN F7 [get_ports {eth_rxd[3]}]
set_property PACKAGE_PIN G8 [get_ports {eth_rxd[2]}]
set_property PACKAGE_PIN F6 [get_ports {eth_rxd[1]}]
set_property PACKAGE_PIN G6 [get_ports {eth_rxd[0]}]
set_property PACKAGE_PIN D9 [get_ports {eth_txd[3]}]
set_property PACKAGE_PIN E9 [get_ports {eth_txd[2]}]
set_property PACKAGE_PIN E8 [get_ports {eth_txd[1]}]
set_property PACKAGE_PIN D7 [get_ports {eth_txd[0]}]
set_property PACKAGE_PIN E5 [get_ports eth_rxc]
set_property PACKAGE_PIN F8 [get_ports eth_tx_ctl]
set_property PACKAGE_PIN D6 [get_ports eth_txc]
set_property PACKAGE_PIN D5 [get_ports eth_rx_ctl]

#按键
set_property -dict {PACKAGE_PIN AD10 IOSTANDARD LVCMOS33} [get_ports key0]
#LED灯
set_property -dict {PACKAGE_PIN AE10 IOSTANDARD LVCMOS33} [get_ports {led[0]}]
set_property -dict {PACKAGE_PIN AF10 IOSTANDARD LVCMOS33} [get_ports {led[1]}]

# #HDMI
# set_property -dict {PACKAGE_PIN G3 IOSTANDARD LVDS} [get_ports {tmds_data_p[2]}]
# set_property -dict {PACKAGE_PIN F2 IOSTANDARD LVDS} [get_ports {tmds_data_p[1]}]
# set_property -dict {PACKAGE_PIN G1 IOSTANDARD LVDS} [get_ports {tmds_data_p[0]}]
# set_property -dict {PACKAGE_PIN E1 IOSTANDARD LVDS} [get_ports tmds_clk_p]




