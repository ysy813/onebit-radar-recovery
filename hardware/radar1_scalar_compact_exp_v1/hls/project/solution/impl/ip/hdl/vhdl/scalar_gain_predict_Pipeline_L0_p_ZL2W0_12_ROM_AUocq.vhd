-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_12_ROM_AUocq is 
    generic(
             DataWidth     : integer := 20; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_12_ROM_AUocq is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11001001010010101001", 1 => "11111101100001000011", 
    2 => "11110011110001001010", 3 => "11010010000111100111", 
    4 => "11110000010010110111", 5 => "11100100010110101110", 
    6 => "00000001010101001101", 7 => "00010011100111010101", 
    8 => "11111110000111000111", 9 => "11000110100100100101", 
    10 => "00001100111000111100", 11 => "11111010101000110000", 
    12 => "00000101010011011011", 13 => "11000100011011000111", 
    14 => "00000010100100000000", 15 => "00000000010110010010", 
    16 => "00000010001101011110", 17 => "00000101110100111111", 
    18 => "00000101010010111010", 19 => "11001110001101111011", 
    20 => "11111111001000001110", 21 => "00001000010110011000", 
    22 => "11111000100101000110", 23 => "11111111011011101100", 
    24 => "11011010101010010000", 25 => "11111011010101000001", 
    26 => "00000000101001111011", 27 => "11100111010000000111", 
    28 => "11101011110100000001", 29 => "10110110101110011010", 
    30 => "11111111101111011011", 31 => "00000010010101100001" );


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

