-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_14_ROM_AUqcK is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_14_ROM_AUqcK is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11011011100101110", 1 => "00000110101110011", 
    2 => "11110100011111001", 3 => "11000001010011101", 
    4 => "00101111000100011", 5 => "10100000000110011", 
    6 => "11011110101101010", 7 => "11010010010100001", 
    8 => "11111011100000011", 9 => "00111100110111010", 
    10 => "00010101000011110", 11 => "11111010001001101", 
    12 => "11110000111001110", 13 => "11111000100000011", 
    14 => "11100010110010110", 15 => "00101100001011000", 
    16 => "00010100010011100", 17 => "10101011010010100", 
    18 => "01011101110100101", 19 => "11101101100100010", 
    20 => "00010100001111000", 21 => "11001100011000110", 
    22 => "11101010011011000", 23 => "00001001100001010", 
    24 => "00000000101100001", 25 => "00100110001111110", 
    26 => "11011101011001101", 27 => "11011100110001101", 
    28 => "00011101001000001", 29 => "00011101111111110", 
    30 => "11110101110001010", 31 => "00011100101011110" );


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

