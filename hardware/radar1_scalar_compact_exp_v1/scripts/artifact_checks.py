from pathlib import Path
import hashlib,json,re,struct
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"pkg"
MODES=dict(raw_imaging=1,onebit_bypass=5,onebit_network=13,onebit_network_storage=15)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def bus_skew_check():
    report=(ROOT/'reports/bus_skew.rpt').read_text(errors='replace')
    summary=re.search(r'1\. Bus Skew Report Summary\s*\n-+\n(.*?)\n2\. Bus Skew Report Per Constraint\s*\n-+\n',report,re.S)
    assert summary,'Bus skew report summary is missing'
    blocks=re.split(r'(?m)^(?=\d+\s+\d+\s+)',summary[1])[1:]
    rows=[];unclocked_camera=0
    for block in blocks:
        row=re.search(r'^\s+(?:Slow|Fast)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$',block,re.M)
        if row:rows.append(row.groups());continue
        # The unused legacy camera WRITE FIFO has no external camera clock.
        # Report its NA separately; never call it a passing skew measurement.
        assert 'cam_axi_data_0/inst/AXI_DMA_v1_0_M00_AXI_inst/u_fifo_cc/' in block and re.search(r'^\s+NA\s+\d+\.\d+\s+NA\s+NA\s*$',block,re.M),('Unexpected unanalyzed bus skew constraint',block[:180])
        unclocked_camera+=1
    assert rows and unclocked_camera==2,('Unexpected legacy camera constraint count',unclocked_camera)
    assert 'Slack (VIOLATED)' not in report
    slacks=[float(r[2]) for r in rows]
    assert min(slacks)>=0,('Bus skew timing must pass',min(slacks))
    return dict(status='ANALYZED_CONSTRAINTS_PASS',constraints_total=len(blocks),constraints_checked=len(rows),
                legacy_camera_constraints_unanalyzed=unclocked_camera,worst_slack_ns=min(slacks))

def elf_check(path):
    data=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
    assert h[0][:6]==b'\x7fELF\x02\x01'
    end=0
    for i in range(h[10]):
        p=struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9])
        if p[0]==1 and p[6]:
            assert all(0x100000<=a and a+p[6]<=0x02000000 for a in [p[3],p[4]])
            end=max(end,p[3]+p[6])
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*h[11]) for i in range(h[12])]
    symbols=set();table=False
    for s in sections:
        if s[1]!=2:continue
        st=sections[s[6]];strings=data[st[4]:st[4]+st[5]]
        for off in range(s[4],s[4]+s[5],s[9]):
            n,_,_,index,address,_=struct.unpack_from('<IBBHQQ',data,off)
            name=strings[n:strings.find(b'\0',n)].decode(errors='replace');symbols.add(name)
            if name=='_binary_aq_ar_bin_start':
                sec=sections[index];start=sec[4]+address-sec[3]
                table=data[start:start+11377128]==(ROOT/'software/aq_ar.bin').read_bytes()
    assert table,path.name
    assert b'NETWORK_REQUEST=%u' in data and b'NET: enabled=%u' in data
    if path.stem!='onebit_network_storage':assert 'f_mount' not in symbols and not any(n.startswith('XAxiDma_') for n in symbols)
    else:assert b'radar1-scalar-compact-exp-v1' in data and 'f_mount' in symbols
    return dict(sha256=sha(path),load_end_exclusive=f'0x{end:08x}',aq_ar_exact=True)
