-- ==============================================================
-- Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2022.1 (64-bit)
-- Tool Version Limit: 2022.04
-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- ==============================================================
library ieee; 
use ieee.std_logic_1164.all; 
use ieee.std_logic_unsigned.all;

entity scalar_gain_predict_Pipeline_L0_p_ZL2W0_23_ROM_AUzec is 
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


architecture rtl of scalar_gain_predict_Pipeline_L0_p_ZL2W0_23_ROM_AUzec is 

signal address0_tmp : std_logic_vector(AddressWidth-1 downto 0); 
type mem_array is array (0 to AddressRange-1) of std_logic_vector (DataWidth-1 downto 0); 
signal mem : mem_array := (
    0 => "0001000101111000", 1 => "0000000000000000", 2 => "0011101110011000", 
    3 => "1010100011110101", 4 => "1101100100001000", 5 => "1111110101101110", 
    6 => "0000001001000000", 7 => "0001110001101101", 8 => "1111010101011100", 
    9 => "0101101101111001", 10 => "0010000000010000", 11 => "0001001011110101", 
    12 => "0001011100011100", 13 => "1111111110111100", 14 => "0010101101110011", 
    15 => "1110111100111100", 16 => "0000000000000000", 17 => "0001010000001101", 
    18 => "0010001001100000", 19 => "0010011100100000", 20 => "0000000000000000", 
    21 => "0000100111001001", 22 => "0010011000011100", 23 => "1101100001000000", 
    24 => "1111011001010000", 25 => "0010010101111001", 26 => "1101110101111001", 
    27 => "1110100010100010", 28 => "1111100001011000", 29 => "0101100100010110", 
    30 => "0000000000000000", 31 => "1111111011111111" );


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

