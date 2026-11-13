-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_31_ROM_AUHfu is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_31_ROM_AUHfu is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "111100111000110", 1 => "000000000000000", 2 => "000000110001000", 
    3 => "110001000011101", 4 => "111001011111111", 5 => "110110100001100", 
    6 => "110111001000011", 7 => "101100000010100", 8 => "111111100010011", 
    9 => "001011010100110", 10 => "111011100011011", 11 => "101101001011101", 
    12 => "111100111001001", 13 => "000111000110111", 14 => "110101001011110", 
    15 => "000001001011101", 16 => "000000000000000", 17 => "111000010100000", 
    18 => "101100110111101", 19 => "111111111010011", 20 => "000000000000000", 
    21 => "110110101110111", 22 => "111001110110000", 23 => "001101110110010", 
    24 => "111010000111101", 25 => "010000001010011", 26 => "000110100010110", 
    27 => "000111111011010", 28 => "110100111010101", 29 => "110001011011011", 
    30 => "000000000000000", 31 => "111111011101111" );


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

