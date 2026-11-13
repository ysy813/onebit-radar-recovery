-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_29_ROM_AUFfa is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_29_ROM_AUFfa is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "1001101010011110", 1 => "0000000000000000", 2 => "1110111010111100", 
    3 => "1011001010000111", 4 => "1101100100111100", 5 => "0001101011011110", 
    6 => "1111001011100010", 7 => "0100100011011001", 8 => "1101001100101100", 
    9 => "1110110000111101", 10 => "0000100011100111", 11 => "0100001000001011", 
    12 => "1111010010110001", 13 => "1101000101011100", 14 => "0001001110000111", 
    15 => "1010100110010010", 16 => "0000000000000000", 17 => "1111101111000110", 
    18 => "1110101101011010", 19 => "1111010000111001", 20 => "0000000000000000", 
    21 => "0010111011001011", 22 => "0010000110111001", 23 => "1111101110111101", 
    24 => "0011110110101000", 25 => "0000110001001000", 26 => "0001011111100010", 
    27 => "0000000000010000", 28 => "0111110100010100", 29 => "1011111101101101", 
    30 => "0000000000000000", 31 => "1111111011001000" );


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

