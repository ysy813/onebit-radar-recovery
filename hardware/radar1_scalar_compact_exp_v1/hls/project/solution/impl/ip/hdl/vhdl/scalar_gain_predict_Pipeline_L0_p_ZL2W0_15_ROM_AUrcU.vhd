-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_15_ROM_AUrcU is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_15_ROM_AUrcU is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "000000111011001100", 1 => "111111010000111010", 
    2 => "000011000100001100", 3 => "101110001101100011", 
    4 => "000010000101110011", 5 => "111010001011111100", 
    6 => "000001000101110001", 7 => "010111111011011000", 
    8 => "000011001010100111", 9 => "000001110000000110", 
    10 => "111100010101100011", 11 => "111100101101000101", 
    12 => "000011100010000101", 13 => "000000000000010100", 
    14 => "000001111010001001", 15 => "000100001110001010", 
    16 => "111101011111010110", 17 => "000101110010100110", 
    18 => "111110100000110001", 19 => "111111101010011111", 
    20 => "111111011011001101", 21 => "111100000110101000", 
    22 => "000001011111110101", 23 => "000000110000000001", 
    24 => "000011000110101000", 25 => "111010111101010010", 
    26 => "000100000101101111", 27 => "000011000110001101", 
    28 => "000110010101000110", 29 => "000111001110110111", 
    30 => "111101011100100111", 31 => "000000001100101001" );


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

