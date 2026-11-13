-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_10_ROM_AUmb6 is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_10_ROM_AUmb6 is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11101010010011001010", 1 => "00000010011100011000", 
    2 => "00001101110101101000", 3 => "11111011111000011010", 
    4 => "00001010011010000111", 5 => "11101110001101000001", 
    6 => "11111010001010100110", 7 => "10111111010010100111", 
    8 => "00000001100000010110", 9 => "11111000001011010110", 
    10 => "00000101001010101010", 11 => "00000001111001001111", 
    12 => "00000111110010001111", 13 => "00000110111011111000", 
    14 => "00000001010110101010", 15 => "00000000101111010001", 
    16 => "00000000011001011011", 17 => "00000011000100101010", 
    18 => "11110011110011101010", 19 => "00000001000000101100", 
    20 => "00000001010110100101", 21 => "00001111110000010101", 
    22 => "11111100101011000011", 23 => "00000110001010000101", 
    24 => "11111011000011000111", 25 => "11111101001011010000", 
    26 => "11111011101001000011", 27 => "00001010111011111101", 
    28 => "00000100101100011101", 29 => "00000010110111000001", 
    30 => "00000001110001101001", 31 => "00000010001000101100" );


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

