-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_13_ROM_AUpcA is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_13_ROM_AUpcA is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "111000110010110110", 1 => "111110110011101110", 
    2 => "000100110110101111", 3 => "101110100011011111", 
    4 => "110101111001101000", 5 => "110110100000110000", 
    6 => "111001000111011110", 7 => "110011011100010000", 
    8 => "111100110000000101", 9 => "111101001000001000", 
    10 => "000000010111110110", 11 => "000000001000110001", 
    12 => "111010110110001111", 13 => "111100110111000000", 
    14 => "000001001111111100", 15 => "111111010000000011", 
    16 => "111111100101111011", 17 => "111001010000001001", 
    18 => "111111010111100011", 19 => "111011001101111111", 
    20 => "000000101000111110", 21 => "000100101101110111", 
    22 => "111101110100011101", 23 => "111100001110100011", 
    24 => "111110010001011101", 25 => "111111110001110111", 
    26 => "000001001001101111", 27 => "111111000000001001", 
    28 => "000010000011001111", 29 => "111101110010110101", 
    30 => "000000011010000101", 31 => "111101010010101000" );


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

