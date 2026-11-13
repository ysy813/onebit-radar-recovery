-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_1_ROM_AUTdEe is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_1_ROM_AUTdEe is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "001000111111111110", 1 => "111111101110110110", 
    2 => "111010001111110100", 3 => "000111001000100101", 
    4 => "111101110011110010", 5 => "001010011100001011", 
    6 => "000101000000010111", 7 => "000101110000111011", 
    8 => "000110010101010111", 9 => "111100000001011010", 
    10 => "111110000101000010", 11 => "001001111101101100", 
    12 => "111011111000100000", 13 => "111100001101001101", 
    14 => "000001000100110111", 15 => "001000001010011100", 
    16 => "111101000000100110", 17 => "000000101101011000", 
    18 => "000011100111110100", 19 => "111110111110011010", 
    20 => "000000110100110001", 21 => "111100010010111100", 
    22 => "000001101100101011", 23 => "000111001011010110", 
    24 => "000101110010010000", 25 => "000100010011100011", 
    26 => "000111101101010111", 27 => "000110110001000010", 
    28 => "010000100001100111", 29 => "111000010010111110", 
    30 => "111101010010101001", 31 => "111101110001010100" );


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

