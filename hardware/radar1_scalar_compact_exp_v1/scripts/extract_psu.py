from pathlib import Path
import zipfile
R=Path(__file__).resolve().parents[1]
with zipfile.ZipFile(R/'pkg/scalar_network.xsa') as z:
 names=[n for n in z.namelist() if n.endswith('psu_init.tcl')]
 assert len(names)==1
 (R/'pkg/psu_init.tcl').write_bytes(z.read(names[0]))
print('FINAL_XSA_PSU_INIT_EXTRACTED')
