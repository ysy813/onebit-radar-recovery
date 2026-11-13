-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_5_ROM_AUThbi is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_5_ROM_AUThbi is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0001110101001011", 1 => "0000001111010111", 2 => "0100010000101101", 
    3 => "0100001110000001", 4 => "0011001110001000", 5 => "0000001110000001", 
    6 => "0110111011001111", 7 => "1000010111100000", 8 => "1111111011110110", 
    9 => "0010100001110111", 10 => "0100111011011010", 11 => "1100011111011101", 
    12 => "0101001101111000", 13 => "0001001100011100", 14 => "1110001011101100", 
    15 => "1111111000011101", 16 => "0010101101111101", 17 => "0000001101001111", 
    18 => "1000001011011010", 19 => "0011101001010110", 20 => "0000000011011100", 
    21 => "1010101101101001", 22 => "0001101100010000", 23 => "0010010111111010", 
    24 => "0100110101001110", 25 => "0100001100000010", 26 => "0001101100010011", 
    27 => "0000100110011101", 28 => "1110111111110100", 29 => "1111110011100010", 
    30 => "1100101100000001", 31 => "1100000111101100" );


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

