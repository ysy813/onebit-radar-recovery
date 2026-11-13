-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_34_ROM_AUKfY is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_34_ROM_AUKfY is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0000101010001001", 1 => "0000000000000000", 2 => "0000010010011000", 
    3 => "0010111101101000", 4 => "0001000010100110", 5 => "0000011001101000", 
    6 => "1111111011110111", 7 => "1111001001110100", 8 => "0000101000101100", 
    9 => "1111101100010101", 10 => "0000100001110111", 11 => "1111111011001100", 
    12 => "0000100010101111", 13 => "1111010101110000", 14 => "0000010101000101", 
    15 => "1111111101110010", 16 => "0000000000000000", 17 => "0000110100111100", 
    18 => "1011111001001010", 19 => "1111101111101101", 20 => "0000000000000000", 
    21 => "1111011111000110", 22 => "1110000110011001", 23 => "0001000000101110", 
    24 => "1111011011011111", 25 => "0000110111110011", 26 => "0000011001101110", 
    27 => "0000111100001101", 28 => "1111110011000111", 29 => "1110001000101110", 
    30 => "0000000000000000", 31 => "1111111100100101" );


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

