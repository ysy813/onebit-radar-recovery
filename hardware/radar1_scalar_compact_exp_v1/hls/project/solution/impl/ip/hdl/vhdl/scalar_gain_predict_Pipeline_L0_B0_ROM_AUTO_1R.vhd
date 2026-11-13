-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_B0_ROM_AUTO_1R is 
    generic(
             DataWidth     : integer := 33; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_B0_ROM_AUTO_1R is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "111000010011111100111110000000000", 
    1 => "111010110010110111101010010000000", 
    2 => "001000110000110000110011110000000", 
    3 => "110100110011100110010010010000000", 
    4 => "101100101000110110001000100000000", 
    5 => "001100000011100101110101110000000", 
    6 => "111001010100110100011111010000000", 
    7 => "111110100110110000001100000110000", 
    8 => "110101100001101110110110100000000", 
    9 => "111100011010110100001010100100000", 
    10 => "010001100110101110010101100000000", 
    11 => "111010100110000000010000000000000", 
    12 => "010000001011101000001100100000000", 
    13 => "101011110001100011100110000000000", 
    14 => "001111001000011110010000110000000", 
    15 => "110010111010001001010011110000000", 
    16 => "111011110001011000000011000000000", 
    17 => "110010111100101010000100000000000", 
    18 => "001100100100001001011010100000000", 
    19 => "001011001101000010110111000000000", 
    20 => "111001101110000100111010000000000", 
    21 => "001001010111010110011000110000000", 
    22 => "110100100010110101001110110000000", 
    23 => "110111000111001000111000110000000", 
    24 => "110101011000100101010010110000000", 
    25 => "000111001001110011001100111000000", 
    26 => "000001000101101001111111011000000", 
    27 => "110000010000001101111000110000000", 
    28 => "110111000010000001110100000000000", 
    29 => "000011001001001111010101110000000", 
    30 => "111010000110011000110000000000000", 
    31 => "111110100100001111101111101000000" );


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

