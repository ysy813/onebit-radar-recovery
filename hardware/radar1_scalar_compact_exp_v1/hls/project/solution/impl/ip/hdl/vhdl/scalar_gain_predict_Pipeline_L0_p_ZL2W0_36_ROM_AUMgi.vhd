-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_36_ROM_AUMgi is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_36_ROM_AUMgi is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "110100101100101", 1 => "000000000000000", 2 => "111000011111000", 
    3 => "001111011001101", 4 => "011110000000010", 5 => "111100110011011", 
    6 => "101000011011110", 7 => "110101110100110", 8 => "001010111001010", 
    9 => "010111001011100", 10 => "111110010011011", 11 => "111010000011100", 
    12 => "111100000110101", 13 => "110011000100100", 14 => "110100110010010", 
    15 => "111111010111111", 16 => "000000000000000", 17 => "111011000010110", 
    18 => "101110100101101", 19 => "000110101011100", 20 => "000000000000000", 
    21 => "111000110000111", 22 => "111010111001110", 23 => "010000011100100", 
    24 => "000000001011011", 25 => "000111011101110", 26 => "001101010101000", 
    27 => "000011000010011", 28 => "101010110000100", 29 => "101101101111000", 
    30 => "000000000000000", 31 => "111111011101101" );


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

