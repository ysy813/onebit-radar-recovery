-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_22_ROM_AUyd2 is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_22_ROM_AUyd2 is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "001010011111111", 1 => "000000000000000", 2 => "010011010100110", 
    3 => "000111000011110", 4 => "111011000001000", 5 => "111011101000110", 
    6 => "110111110001101", 7 => "100110001001111", 8 => "111001101010000", 
    9 => "101100011100011", 10 => "000110000110101", 11 => "110100111000011", 
    12 => "111111000011001", 13 => "010101110100101", 14 => "000110111010000", 
    15 => "001100001101000", 16 => "000000000000000", 17 => "110010110110100", 
    18 => "001110001111000", 19 => "000110100101111", 20 => "000000000000000", 
    21 => "011100111100100", 22 => "101110011001010", 23 => "111101110110000", 
    24 => "000100101101101", 25 => "001101011001010", 26 => "111010011000101", 
    27 => "001110001111110", 28 => "111101000010010", 29 => "111011111101111", 
    30 => "000000000000000", 31 => "111111100101101" );


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

