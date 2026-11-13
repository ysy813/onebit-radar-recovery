-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_26_ROM_AUCeG is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_26_ROM_AUCeG is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11010111011000001", 1 => "00000000000000000", 
    2 => "11111011101110101", 3 => "11101100100110101", 
    4 => "11011000111011110", 5 => "00001110001111111", 
    6 => "11111100110011001", 7 => "00110111010101000", 
    8 => "11011111111001100", 9 => "11101001001110100", 
    10 => "00001001011100011", 11 => "00011101100100111", 
    12 => "11111101100111011", 13 => "11110001101011001", 
    14 => "00001011010111001", 15 => "11001010001000110", 
    16 => "00000000000000000", 17 => "00001101000000111", 
    18 => "11110110000111000", 19 => "00000000111001001", 
    20 => "00000000000000000", 21 => "00011100011110010", 
    22 => "00000101110110000", 23 => "11111100101111010", 
    24 => "00010110111000100", 25 => "00001000001000010", 
    26 => "00001100010111010", 27 => "11111100110110011", 
    28 => "01000010011000001", 29 => "11100111011110100", 
    30 => "00000000000000000", 31 => "11111111011110111" );


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

