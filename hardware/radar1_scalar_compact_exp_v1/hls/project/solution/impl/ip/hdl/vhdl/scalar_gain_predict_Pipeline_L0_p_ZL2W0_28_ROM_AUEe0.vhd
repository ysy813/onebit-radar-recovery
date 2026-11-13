-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_28_ROM_AUEe0 is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_28_ROM_AUEe0 is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0010000111001010", 1 => "0000000000000000", 2 => "1110001111000101", 
    3 => "0000101011111010", 4 => "0010000001111001", 5 => "1101000100100000", 
    6 => "1111001111001101", 7 => "1110111110001000", 8 => "0010010111010000", 
    9 => "1101100101111111", 10 => "1111001110001000", 11 => "1100010001111011", 
    12 => "0001011001100100", 13 => "0000111000011111", 14 => "1101000111100100", 
    15 => "0011110010011010", 16 => "0000000000000000", 17 => "1011100101111011", 
    18 => "1101001111010001", 19 => "0000110101100100", 20 => "0000000000000000", 
    21 => "1100001011000011", 22 => "0000000011110011", 23 => "0011001100110001", 
    24 => "0010100110001100", 25 => "1111010101000101", 26 => "0001010111011101", 
    27 => "0010001000011101", 28 => "1111110101010001", 29 => "0000001101001101", 
    30 => "0000000000000000", 31 => "1111111010111100" );


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

