-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_39_ROM_AUPgM is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_39_ROM_AUPgM is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "110101010110111", 1 => "000000000000000", 2 => "001111110111111", 
    3 => "001000110111100", 4 => "010101110010010", 5 => "001001111011001", 
    6 => "110010101011000", 7 => "111100100001100", 8 => "110111110000001", 
    9 => "101010110011011", 10 => "111111111111110", 11 => "000111011101001", 
    12 => "111111010000110", 13 => "010111010010010", 14 => "000100011100100", 
    15 => "111111100100011", 16 => "000000000000000", 17 => "110010111011100", 
    18 => "111111000001111", 19 => "111000100111000", 20 => "000000000000000", 
    21 => "111101100111101", 22 => "111110001100110", 23 => "000111101000100", 
    24 => "000000110011011", 25 => "000000011011000", 26 => "111011011111111", 
    27 => "000111000111101", 28 => "101101010011110", 29 => "111001010001011", 
    30 => "000000000000000", 31 => "111111011001011" );


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

