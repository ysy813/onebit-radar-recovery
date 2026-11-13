-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_38_ROM_AUOgC is 
    generic(
             DataWidth     : integer := 15; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_38_ROM_AUOgC is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "111110101010111", 1 => "000000000000000", 2 => "000001011111100", 
    3 => "101000101110101", 4 => "000101001100010", 5 => "000101110111000", 
    6 => "101011111010101", 7 => "111011101110011", 8 => "001001111000110", 
    9 => "101100011111111", 10 => "111010100010010", 11 => "111110101100000", 
    12 => "111000001101110", 13 => "111111011000111", 14 => "111000001101011", 
    15 => "001100001010110", 16 => "000000000000000", 17 => "101111011110001", 
    18 => "111011000101000", 19 => "000000101100101", 20 => "000000000000000", 
    21 => "101000100001100", 22 => "110011001001000", 23 => "001110011000001", 
    24 => "000010110101001", 25 => "000100100101110", 26 => "000111001111010", 
    27 => "000100111111011", 28 => "110100110010110", 29 => "110011000001010", 
    30 => "000000000000000", 31 => "111111011100101" );


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

