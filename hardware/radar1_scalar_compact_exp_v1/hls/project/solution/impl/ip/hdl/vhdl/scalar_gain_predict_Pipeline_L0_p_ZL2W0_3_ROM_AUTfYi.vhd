-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_3_ROM_AUTfYi is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_3_ROM_AUTfYi is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "00100110000001100", 1 => "11101011011110111", 
    2 => "11111111100101100", 3 => "00100000010011111", 
    4 => "00011000111010010", 5 => "00011100010010000", 
    6 => "00011010101011111", 7 => "00010011000011011", 
    8 => "11101010100011111", 9 => "00010110011001101", 
    10 => "00000001111011111", 11 => "11011101111100001", 
    12 => "00101110111010010", 13 => "00111100111010000", 
    14 => "00011000001101010", 15 => "00100010110100100", 
    16 => "11101100001001101", 17 => "00111110101100000", 
    18 => "11110001011010110", 19 => "00101100001010000", 
    20 => "11100000101000100", 21 => "00001010011001001", 
    22 => "11110011000000011", 23 => "00001111101010010", 
    24 => "00011110100101001", 25 => "00010001101101010", 
    26 => "00011110110000000", 27 => "00010000000011101", 
    28 => "11100001010011111", 29 => "01010010110010000", 
    30 => "00000000011011101", 31 => "11111010111101001" );


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

