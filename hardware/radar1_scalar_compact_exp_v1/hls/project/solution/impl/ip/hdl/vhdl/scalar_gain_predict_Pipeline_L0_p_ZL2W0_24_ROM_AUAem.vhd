-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_24_ROM_AUAem is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_24_ROM_AUAem is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0001110000101011", 1 => "0000000000000000", 2 => "0000101001010110", 
    3 => "1010001111000011", 4 => "1110010011100010", 5 => "1110010010001011", 
    6 => "1111100011111110", 7 => "1101111111011011", 8 => "0000111100101100", 
    9 => "1101100100100000", 10 => "0000110001110000", 11 => "1111101010111101", 
    12 => "0000101100111100", 13 => "1101101001011000", 14 => "1111110010010001", 
    15 => "0010111011011001", 16 => "0000000000000000", 17 => "1110010110000100", 
    18 => "1111010011101100", 19 => "0001110101110001", 20 => "0000000000000000", 
    21 => "1110100111001100", 22 => "1110100101110100", 23 => "0001000001010011", 
    24 => "1111111111000110", 25 => "0001101110011001", 26 => "0000000111000111", 
    27 => "0000011110110110", 28 => "0000101111110001", 29 => "1111111011101101", 
    30 => "0000000000000000", 31 => "1111111011110011" );


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

