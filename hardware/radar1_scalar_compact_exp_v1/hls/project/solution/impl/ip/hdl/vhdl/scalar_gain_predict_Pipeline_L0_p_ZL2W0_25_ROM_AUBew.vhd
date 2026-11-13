-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_25_ROM_AUBew is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_25_ROM_AUBew is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "100110000010101", 1 => "000000000000000", 2 => "000011101010100", 
    3 => "111101001100110", 4 => "110100011010011", 5 => "110100101001001", 
    6 => "111000001100110", 7 => "111110111000010", 8 => "111110001101000", 
    9 => "000001110100001", 10 => "000010000010000", 11 => "010001100110101", 
    12 => "000000100010010", 13 => "110111101111001", 14 => "000010010001011", 
    15 => "000100001000100", 16 => "000000000000000", 17 => "001000100011000", 
    18 => "111000111010100", 19 => "111110111000010", 20 => "000000000000000", 
    21 => "001011010100100", 22 => "110010111010011", 23 => "000110101011001", 
    24 => "001010001110110", 25 => "000111100001001", 26 => "000100111010000", 
    27 => "000010111000011", 28 => "010101101100101", 29 => "000100110110101", 
    30 => "000000000000000", 31 => "111111010011010" );


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

