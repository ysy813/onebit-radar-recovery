-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_37_ROM_AUNgs is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_37_ROM_AUNgs is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "1111010001001000", 1 => "0000000000000000", 2 => "0000010100000010", 
    3 => "1101001000101000", 4 => "0000110001010011", 5 => "0011011110101100", 
    6 => "1110100110010001", 7 => "0100100000001010", 8 => "1111011100101011", 
    9 => "0001010010011100", 10 => "1101101000010011", 11 => "0011111000101011", 
    12 => "1110101101111001", 13 => "0000111001111001", 14 => "1110101110001100", 
    15 => "1110001110011001", 16 => "0000000000000000", 17 => "1111000011001010", 
    18 => "1111100001101111", 19 => "1101010110101001", 20 => "0000000000000000", 
    21 => "1000010011110010", 22 => "0000001101100011", 23 => "0001101100011010", 
    24 => "1101100001010010", 25 => "0001001010100000", 26 => "1111101100000101", 
    27 => "1111100001100110", 28 => "0000001100010100", 29 => "1101101001101000", 
    30 => "0000000000000000", 31 => "1111111011011011" );


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

