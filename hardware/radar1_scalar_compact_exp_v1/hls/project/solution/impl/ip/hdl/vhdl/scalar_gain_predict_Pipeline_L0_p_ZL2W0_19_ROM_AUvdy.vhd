-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_19_ROM_AUvdy is 
    generic(
             DataWidth     : integer := 16; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_19_ROM_AUvdy is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0000000100101101", 1 => "0000000000000000", 2 => "0000101101100100", 
    3 => "0001000100010001", 4 => "0011101111000000", 5 => "1110000001010101", 
    6 => "1101111101100000", 7 => "1110011110111010", 8 => "0000001010111001", 
    9 => "0100011100110010", 10 => "1111110110100001", 11 => "1111001101000011", 
    12 => "0000100000000001", 13 => "0000101011010110", 14 => "1111001110101110", 
    15 => "1111100111111100", 16 => "0000000000000000", 17 => "1110101010100100", 
    18 => "0000011011000111", 19 => "0001001100110101", 20 => "0000000000000000", 
    21 => "0011000101100111", 22 => "1111001111110111", 23 => "0001010110010000", 
    24 => "0001100000001011", 25 => "1111000011010111", 26 => "1111101011000111", 
    27 => "0000110001010111", 28 => "1101010010110011", 29 => "0010001011011110", 
    30 => "0000000000000000", 31 => "1111111011101000" );


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

