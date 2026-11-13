-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_0_ROM_AUTcud is 
    generic(
             DataWidth     : integer := 17; 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_0_ROM_AUTcud is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "11111101001000100", 1 => "11111100010000010", 
    2 => "00110111110011011", 3 => "00001100000000010", 
    4 => "00000010001110111", 5 => "10110110001110001", 
    6 => "01000110011111111", 7 => "11011001100100001", 
    8 => "00111010011101000", 9 => "00100010001001000", 
    10 => "00110110101010001", 11 => "00001111111010010", 
    12 => "01100011111001101", 13 => "00000110110010101", 
    14 => "00101010111001010", 15 => "00111000010110001", 
    16 => "00000100011011111", 17 => "00001110010100001", 
    18 => "00101001011001010", 19 => "00101101011011010", 
    20 => "11111100011110010", 21 => "00010001100011101", 
    22 => "11110001010001000", 23 => "11110001110110111", 
    24 => "11101111101111110", 25 => "11001111011010110", 
    26 => "11101101000101110", 27 => "00001011001010000", 
    28 => "11110010101101111", 29 => "11000110101111010", 
    30 => "11111000000011001", 31 => "11111110110100110" );


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

