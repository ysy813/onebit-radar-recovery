-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_6_ROM_AUTibs is 
    generic(
             DataWidth     : integer := 17; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_6_ROM_AUTibs is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "00001011000111010", 1 => "11101011000100101", 
    2 => "00110001011010010", 3 => "00101100100011110", 
    4 => "00000001111011101", 5 => "00010011000101111", 
    6 => "11110111101001100", 7 => "11001111001101001", 
    8 => "00000011100000110", 9 => "00001011001001001", 
    10 => "11111101011111011", 11 => "00001001110001100", 
    12 => "00101010110101000", 13 => "11101001111111000", 
    14 => "11111000100000010", 15 => "11100101101001101", 
    16 => "11100101011011110", 17 => "01010001100100010", 
    18 => "00001010111110101", 19 => "11010101101110100", 
    20 => "11111100111111110", 21 => "00110011000100110", 
    22 => "00100000110000110", 23 => "00001111101111111", 
    24 => "00011001011001011", 25 => "11110011001011111", 
    26 => "11010000000011111", 27 => "11010111011001011", 
    28 => "00000110001010010", 29 => "11111010000100101", 
    30 => "11101111110000101", 31 => "11111000000111010" );


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

