-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_11_ROM_AUncg is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_11_ROM_AUncg is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11111110100101101011", 1 => "00000001110101100000", 
    2 => "11111110001010001101", 3 => "11000011000011111011", 
    4 => "00000010011101111100", 5 => "00000010110100111100", 
    6 => "11111000011110011011", 7 => "10111101011010101110", 
    8 => "11110000100110010000", 9 => "00000000011111001000", 
    10 => "00001000101011111110", 11 => "11111100110011101100", 
    12 => "00000000111011010000", 13 => "11111101010100101110", 
    14 => "00000111010001000111", 15 => "00000100100011101110", 
    16 => "00000000100110111110", 17 => "00001001100111011100", 
    18 => "11111101011000110000", 19 => "00001000100010000101", 
    20 => "11111100101011100110", 21 => "11101111110101001010", 
    22 => "00000100000001100000", 23 => "11111011011101010100", 
    24 => "11111110001000111000", 25 => "00001001101011101111", 
    26 => "00000011001001100100", 27 => "11111110100100001000", 
    28 => "11111001101110000010", 29 => "11111111111101000101", 
    30 => "11111100100011011010", 31 => "11111101001001100111" );


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

