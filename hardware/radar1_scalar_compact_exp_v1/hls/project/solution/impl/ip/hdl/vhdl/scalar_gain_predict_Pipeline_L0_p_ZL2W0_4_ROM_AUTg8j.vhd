-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_4_ROM_AUTg8j is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_4_ROM_AUTg8j is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "00001101110111100", 1 => "11110100101001110", 
    2 => "00011111111001001", 3 => "00001101010111010", 
    4 => "00011101100100110", 5 => "00000111111110100", 
    6 => "00101100110101000", 7 => "11011000010010011", 
    8 => "00001110111001010", 9 => "00001001110101111", 
    10 => "00000000001110011", 11 => "11100011001110111", 
    12 => "00000110001101100", 13 => "00100111101100111", 
    14 => "11110100100101011", 15 => "00000111011110010", 
    16 => "11101010010110110", 17 => "01000110101111000", 
    18 => "00000000001010001", 19 => "00001110010010101", 
    20 => "11100110111100001", 21 => "00000101111110000", 
    22 => "00011001100101000", 23 => "00000000001010111", 
    24 => "11101010000010101", 25 => "11100000011010111", 
    26 => "11110111101000011", 27 => "00000010111000000", 
    28 => "11101110001001110", 29 => "00001101100011110", 
    30 => "11110111010000100", 31 => "00000010011110011" );


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

