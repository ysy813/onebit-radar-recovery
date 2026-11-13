-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_27_ROM_AUDeQ is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_27_ROM_AUDeQ is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0010101111011110", 1 => "0000000000000000", 2 => "0000001110010001", 
    3 => "1101000001110111", 4 => "0010011001000100", 5 => "1110011010111000", 
    6 => "1110100011101011", 7 => "1110010111010100", 8 => "0010011010101010", 
    9 => "1101010011101000", 10 => "0000100100110101", 11 => "1010111110110000", 
    12 => "0001100011100001", 13 => "0010100010110111", 14 => "1110110110011110", 
    15 => "0011001100111101", 16 => "0000000000000000", 17 => "1011101010010010", 
    18 => "0000010011010001", 19 => "0001101000000101", 20 => "0000000000000000", 
    21 => "1110100100111010", 22 => "1111000100001000", 23 => "0001100000111001", 
    24 => "0010111001010000", 25 => "0000100011110110", 26 => "0000101000101011", 
    27 => "0001111110011000", 28 => "0000001100101100", 29 => "1111101101100011", 
    30 => "0000000000000000", 31 => "1111111011100000" );


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

