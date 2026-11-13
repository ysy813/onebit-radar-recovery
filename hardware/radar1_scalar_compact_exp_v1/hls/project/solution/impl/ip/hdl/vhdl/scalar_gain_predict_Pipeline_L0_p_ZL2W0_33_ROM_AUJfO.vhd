-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_33_ROM_AUJfO is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_33_ROM_AUJfO is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "110100101101010", 1 => "000000000000000", 2 => "111101001001011", 
    3 => "001001101110100", 4 => "111110100111100", 5 => "110110101110111", 
    6 => "110100100100100", 7 => "110100001011100", 8 => "000100110010110", 
    9 => "110100101100010", 10 => "000011100111000", 11 => "101011100000000", 
    12 => "000000011010000", 13 => "000011100110001", 14 => "111101110011011", 
    15 => "110111010010101", 16 => "000000000000000", 17 => "010001000111110", 
    18 => "101110100111000", 19 => "000101110011110", 20 => "000000000000000", 
    21 => "110111110011011", 22 => "111000101110001", 23 => "000101011100101", 
    24 => "111000011111000", 25 => "010010100000000", 26 => "001001011001111", 
    27 => "000000110000011", 28 => "101100010100101", 29 => "110100001000100", 
    30 => "000000000000000", 31 => "111111011111001" );


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

