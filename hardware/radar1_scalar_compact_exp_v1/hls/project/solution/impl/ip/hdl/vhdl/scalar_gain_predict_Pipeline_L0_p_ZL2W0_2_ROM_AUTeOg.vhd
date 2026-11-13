-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_2_ROM_AUTeOg is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_2_ROM_AUTeOg is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0111010001110110", 1 => "1111100011110010", 2 => "0010010101101101", 
    3 => "0011101000101001", 4 => "0110001111101010", 5 => "0010011001001011", 
    6 => "1111111001010101", 7 => "0101011010111000", 8 => "0010010000101011", 
    9 => "1111100011101001", 10 => "1100110101110110", 11 => "0010111100011011", 
    12 => "0000001111101110", 13 => "0101111110101010", 14 => "1101101000001010", 
    15 => "0100111111000100", 16 => "0011101001010100", 17 => "0001010001101011", 
    18 => "1100110010100101", 19 => "0101100011111010", 20 => "1110000100110010", 
    21 => "0010011000010010", 22 => "0010000100100011", 23 => "0110111000100001", 
    24 => "1110101001110110", 25 => "0000000111011110", 26 => "0001100110001111", 
    27 => "0011000001111000", 28 => "0010111011001100", 29 => "0001111010001111", 
    30 => "1100100000001000", 31 => "1101001110111011" );


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

