-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_16_ROM_AUsc4 is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_16_ROM_AUsc4 is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "000000110001101", 1 => "000000000000000", 2 => "010110011011011", 
    3 => "100010010000111", 4 => "010000111010011", 5 => "000001001011011", 
    6 => "111011000000111", 7 => "111000100011001", 8 => "111101011011000", 
    9 => "110101011010010", 10 => "000111000111100", 11 => "111110010011011", 
    12 => "001001010010100", 13 => "111110110100111", 14 => "001000011100010", 
    15 => "000010110111011", 16 => "000000000000000", 17 => "110011010011111", 
    18 => "110001111101001", 19 => "000001001101110", 20 => "000000000000000", 
    21 => "111011111100100", 22 => "110100100001100", 23 => "000011011111111", 
    24 => "000101011101010", 25 => "111010001100000", 26 => "110101001101110", 
    27 => "000100100000001", 28 => "111001001000010", 29 => "001011001001000", 
    30 => "000000000000000", 31 => "111111100000110" );


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

