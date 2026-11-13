-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_9_ROM_AUTlbW is 
    generic(
             DataWidth     : integer := 18; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_9_ROM_AUTlbW is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "111001001011000101", 1 => "111111000001001001", 
    2 => "001101000001110101", 3 => "000001100011110011", 
    4 => "000101011110010101", 5 => "110001111110010101", 
    6 => "110111001101011111", 7 => "101000111010010100", 
    8 => "101101111011110101", 9 => "000000111010011111", 
    10 => "001011011111110100", 11 => "110000110000000101", 
    12 => "001111111001101010", 13 => "000010111001101001", 
    14 => "001101111011110101", 15 => "111001000111110110", 
    16 => "111111011010101010", 17 => "111101111011101111", 
    18 => "001000011011111001", 19 => "001010001110010101", 
    20 => "000011010111001110", 21 => "000101011110010010", 
    22 => "111011111010010110", 23 => "111010101110110000", 
    24 => "111001110011110001", 25 => "111000100101010011", 
    26 => "111011011010111001", 27 => "110011010010110101", 
    28 => "111100000111110011", 29 => "111100011100111100", 
    30 => "000001101000011101", 31 => "000000000000100110" );


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

