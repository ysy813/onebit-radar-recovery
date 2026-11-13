-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_20_ROM_AUwdI is 
    generic(
             DataWidth     : integer := 15; 
             AddressWidth     : integer := 5; 
             AddressRange    : integer := 32
    ); 
    port (
          address0      : in std_logic_vector(AddressWidth-1 downto 0); 
          ce0       : in std_logic; 
          q0         : out std_logic_vector(DataWidth-1 downto 0);
          reset     : in std_logic;
          clk       : in std_logic
    ); 
end entity; 


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_20_ROM_AUwdI is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "101110101001110", 1 => "000000000000000", 2 => "010110001011111", 
    3 => "000101100110001", 4 => "010011111000011", 5 => "111111111110100", 
    6 => "101100010111011", 7 => "001001100111100", 8 => "111100111100101", 
    9 => "101001001110000", 10 => "001000001011101", 11 => "000000101010010", 
    12 => "000001101101001", 13 => "000011110101010", 14 => "001101000101011", 
    15 => "111110000010101", 16 => "000000000000000", 17 => "001011100110101", 
    18 => "010010000100010", 19 => "000101100010110", 20 => "000000000000000", 
    21 => "111011100000011", 22 => "111101011010001", 23 => "111011001101100", 
    24 => "010101100101101", 25 => "000110100011001", 26 => "111001100000101", 
    27 => "000110000001111", 28 => "110000010011001", 29 => "001111111011000", 
    30 => "000000000000000", 31 => "111111011100110" );


begin 


memory_access_guard_0: process (address0) 
begin
      address0_tmp <= address0;
--synthesis translate_off
      if (CONV_INTEGER(address0) > AddressRange-1) then
           address0_tmp <= (others => '0');
      else 
           address0_tmp <= address0;
      end if;
--synthesis translate_on
end process;

p_rom_access: process (clk)  
begin 
    if (clk'event and clk = '1') then
        if (ce0 = '1') then 
            q0 <= mem(CONV_INTEGER(address0_tmp)); 
        end if;
    end if;
end process;

end rtl;

