-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_35_ROM_AULf8 is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_35_ROM_AULf8 is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0000001010100101", 1 => "0000000000000000", 2 => "0000101101001101", 
    3 => "0111001011100101", 4 => "1111010000010010", 5 => "0001001011101011", 
    6 => "1110011011010000", 7 => "0000101001001100", 8 => "0000110101100101", 
    9 => "1100010001101100", 10 => "0000011100101000", 11 => "0000111001011010", 
    12 => "1111010000101101", 13 => "1110110000100100", 14 => "0000100010111010", 
    15 => "0000100101001100", 16 => "0000000000000000", 17 => "0010011011000010", 
    18 => "0000111111101111", 19 => "1111011100101110", 20 => "0000000000000000", 
    21 => "0000101000110111", 22 => "0000110101000000", 23 => "0000101110100010", 
    24 => "0010110010101101", 25 => "0000001011101000", 26 => "0001000001001000", 
    27 => "0000110000000010", 28 => "1111101100011111", 29 => "1110100101011111", 
    30 => "0000000000000000", 31 => "1111111100001101" );


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

