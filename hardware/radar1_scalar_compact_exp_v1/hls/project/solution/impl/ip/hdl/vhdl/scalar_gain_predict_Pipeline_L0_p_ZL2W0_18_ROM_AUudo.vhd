-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_18_ROM_AUudo is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_18_ROM_AUudo is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0001111111100111", 1 => "0000000000000000", 2 => "0010100101011110", 
    3 => "1101001101011111", 4 => "0001100001101000", 5 => "0000000110101111", 
    6 => "0010101000001100", 7 => "0100001101101010", 8 => "1111001001000011", 
    9 => "1100001100110111", 10 => "0000101101101011", 11 => "0011001100001010", 
    12 => "0001110010100000", 13 => "0000111111101001", 14 => "0000100111000101", 
    15 => "1110101111111101", 16 => "0000000000000000", 17 => "0000011011000010", 
    18 => "1111111000110010", 19 => "0001110100111010", 20 => "0000000000000000", 
    21 => "1010010010010000", 22 => "1111011100101000", 23 => "0000000101001001", 
    24 => "1110110110111110", 25 => "1111111101110111", 26 => "1101101101011111", 
    27 => "0000000011101011", 28 => "1111010110000000", 29 => "0111001101000100", 
    30 => "0000000000000000", 31 => "1111111011001010" );


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

