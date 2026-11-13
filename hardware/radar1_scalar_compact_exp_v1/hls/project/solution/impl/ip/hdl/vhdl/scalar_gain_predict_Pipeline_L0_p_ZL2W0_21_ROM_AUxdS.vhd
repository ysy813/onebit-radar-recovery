-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_21_ROM_AUxdS is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_21_ROM_AUxdS is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "100000010011101", 1 => "000000000000000", 2 => "001000110101001", 
    3 => "010100000000110", 4 => "001111100110101", 5 => "111011000010001", 
    6 => "110110101101011", 7 => "111011011010011", 8 => "110011010011010", 
    9 => "001010011100001", 10 => "000010000010010", 11 => "000100111110110", 
    12 => "111101111000100", 13 => "000110110000101", 14 => "000100000011110", 
    15 => "110010000101101", 16 => "000000000000000", 17 => "000100110001011", 
    18 => "111010011100110", 19 => "111111010100001", 20 => "000000000000000", 
    21 => "001010111110000", 22 => "111000001101110", 23 => "000101011001011", 
    24 => "000001010011111", 25 => "001100010010100", 26 => "000010101100110", 
    27 => "111111110111001", 28 => "001010100100000", 29 => "000010100010111", 
    30 => "000000000000000", 31 => "111111101100000" );


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

