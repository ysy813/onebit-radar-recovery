-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_7_ROM_AUTjbC is 
    generic(
             DataWidth     : integer := 17; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_7_ROM_AUTjbC is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11110101010000110", 1 => "11100100000101000", 
    2 => "00111101110000001", 3 => "00011001100001011", 
    4 => "01010101001000001", 5 => "11111010100100100", 
    6 => "00001100001111101", 7 => "00010111101101000", 
    8 => "00010101110100110", 9 => "00010101000100000", 
    10 => "11110111001011100", 11 => "00011101000110011", 
    12 => "11110001111100000", 13 => "10100001000000101", 
    14 => "00100100110011110", 15 => "11101000111101000", 
    16 => "11110011100010111", 17 => "00001101011011100", 
    18 => "11111100000110001", 19 => "11101110001011111", 
    20 => "11110110001100100", 21 => "00101001110000011", 
    22 => "01000111111001111", 23 => "00011101111101100", 
    24 => "11111111001100100", 25 => "11000100110111001", 
    26 => "00001011101110010", 27 => "11110110110101110", 
    28 => "11110001110011011", 29 => "11111011111101000", 
    30 => "00001101001010100", 31 => "11100001010010101" );


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

