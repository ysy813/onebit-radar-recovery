create_clock -period 8.000 -name eth_rxc [get_ports eth_rxc]

set_property IOSTANDARD LVCMOS33 [get_ports sys_rst_n]
set_property PACKAGE_PIN AH11 [get_ports sys_rst_n]

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

set_property -dict {PACKAGE_PIN AD11 IOSTANDARD LVCMOS33} [get_ports key]




