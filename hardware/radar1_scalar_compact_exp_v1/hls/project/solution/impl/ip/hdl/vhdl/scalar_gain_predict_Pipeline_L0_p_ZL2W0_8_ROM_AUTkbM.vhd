-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_8_ROM_AUTkbM is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_8_ROM_AUTkbM is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "111111100101110101", 1 => "000001100101110111", 
    2 => "000110010010001001", 3 => "111101100100111000", 
    4 => "000100101110010100", 5 => "101100011101111010", 
    6 => "000001111100110000", 7 => "111000110100001011", 
    8 => "000001110110011000", 9 => "111101000110000101", 
    10 => "000001111101100001", 11 => "111100000111010001", 
    12 => "000010000111110001", 13 => "000001010010001101", 
    14 => "000100111110100101", 15 => "000001011011001101", 
    16 => "111111110010001000", 17 => "111110110000110001", 
    18 => "111101110011010000", 19 => "000000010001010000", 
    20 => "000000100110010001", 21 => "111011000100111000", 
    22 => "111110111011100000", 23 => "111010100000110101", 
    24 => "111100011110100110", 25 => "111010100100111101", 
    26 => "000000010000110000", 27 => "000001001000100000", 
    28 => "111100011100000010", 29 => "000000010010010111", 
    30 => "000001100100110100", 31 => "111101110110000111" );


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

