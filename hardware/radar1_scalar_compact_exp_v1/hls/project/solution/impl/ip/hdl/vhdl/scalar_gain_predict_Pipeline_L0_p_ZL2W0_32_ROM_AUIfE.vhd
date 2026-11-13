-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_32_ROM_AUIfE is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_32_ROM_AUIfE is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "000010001101011", 1 => "000000000000000", 2 => "000101110111000", 
    3 => "000000010110100", 4 => "100000001000000", 5 => "001010101010101", 
    6 => "000000110100100", 7 => "001110001100110", 8 => "111110101110011", 
    9 => "111100111110011", 10 => "111100011101100", 11 => "010010101000010", 
    12 => "111111000110011", 13 => "010001011111111", 14 => "111111011011110", 
    15 => "101001010110001", 16 => "000000000000000", 17 => "000100000010110", 
    18 => "110000001111001", 19 => "000000010010000", 20 => "000000000000000", 
    21 => "111010000100011", 22 => "010011001010010", 23 => "000001111010010", 
    24 => "101011101001011", 25 => "001100000110101", 26 => "111100110010110", 
    27 => "111111000101001", 28 => "111010001010111", 29 => "101000110010011", 
    30 => "000000000000000", 31 => "111111011011110" );


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

