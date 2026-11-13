-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_17_ROM_AUtde is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_17_ROM_AUtde is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "001001010101110", 1 => "000000000000000", 2 => "010001101001101", 
    3 => "011100011101010", 4 => "000101110000110", 5 => "111000101111101", 
    6 => "110110101101001", 7 => "000111000100001", 8 => "000010010010100", 
    9 => "101011110010001", 10 => "001001011100111", 11 => "111110101011101", 
    12 => "000110010100010", 13 => "000011001000110", 14 => "000010101110010", 
    15 => "000001100101010", 16 => "000000000000000", 17 => "111000011101101", 
    18 => "110100010010111", 19 => "001111000110010", 20 => "000000000000000", 
    21 => "101000010111111", 22 => "111000110101000", 23 => "000011111010101", 
    24 => "001000100001100", 25 => "000010110100001", 26 => "111001111110001", 
    27 => "001101111011001", 28 => "101110011111111", 29 => "001100000011010", 
    30 => "000000000000000", 31 => "111111011111111" );


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

