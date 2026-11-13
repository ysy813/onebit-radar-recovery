from pathlib import Path
import sys,json,re
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'model/runtime'))
from restore_power import PowerRestorer
from scalar_guard import apply_guard,local_max
from compact_guard import compact_peak_skip

def transform(f):
    z=f.T.astype('i8')<<4
    def fifth(x):
        y=x.copy()
        for _ in range(4):y=(y*x+32768)>>16
        return y
    v=fifth(z[:,[0,4,5,6,7]])
    return np.concatenate([z[:,:8],v,np.clip(3*v[:,:1]-v[:,1:2],-65536,65536),np.clip(5*v[:,:1]-v[:,2:3],-65536,65536),v[:,:1]-fifth(z[:,2:3]),z[:,8:]],axis=1)

def tb(name,module,width,connections,count,expected_offset,retwidth=32):
    return f'''`timescale 1ns/1ps
module {name};
reg clk=0;always #5 clk=~clk;
reg rst=1,start=0;wire done,idle,ready;wire [{retwidth-1}:0] gain;
reg [{width-1}:0] vectors[0:{count-1}],v;
{module} dut(.ap_clk(clk),.ap_rst(rst),.ap_start(start),.ap_done(done),.ap_idle(idle),.ap_ready(ready),.ap_return(gain),{connections});
integer i,t;
initial begin
 $readmemh("{name}.hex",vectors);repeat(5)@(negedge clk);rst=0;
 for(i=0;i<{count};i=i+1)begin
  @(negedge clk);v=vectors[i];start=1;@(negedge clk);start=0;t=0;
  while(!done&&t<250)begin @(negedge clk);t=t+1;end
  if(!done||gain!==v[{expected_offset}+:16])$fatal(1,"{name} mismatch i=%0d g=%0d expected=%0d",i,gain,v[{expected_offset}+:16]);
 end
 $display("{name.upper()}_PASS cases={count}");$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
'''

def main():
    m=PowerRestorer();p=np.roll(np.fromfile(R/'numeric/weak512/test_power.bin','<u8').reshape(1024,512),-256,1)
    f=m.features(p);raw=m.predict_gain_q14(f);guarded=compact_peak_skip(p,apply_guard(p,raw,m.config['power_guard'],f,512),f,512)
    rng=np.random.default_rng(411102);chosen=np.r_[rng.choice(p.size,256,False),np.flatnonzero(raw.ravel()!=guarded.ravel())[:256]]
    fs=f[:,chosen];x=transform(fs);s=x.copy()
    for i,(w,b) in enumerate(m.layers):
        s=(s@w.T+b+32768)>>16
        if i<2:s=np.maximum(s,0)
    g=m.lut[np.clip(((s[:,0]+32)>>6)+16384,0,32768)]
    assert np.array_equal(g,raw.ravel()[chosen])
    count=len(chosen)
    mlp=[];guards=[];mx3=local_max(p,3).ravel();mx9=local_max(p,9).ravel();flat=p.ravel();peak=int(p.max())
    for j,idx in enumerate(chosen):
        val=sum((int(v)&0xffffffff)<<(32*k) for k,v in enumerate(x[j]));val|=int(g[j])<<1280;mlp.append(f'{val:0324x}')
        vals=[int(flat[idx]),int(mx3[idx]),int(mx9[idx]),peak]
        val=sum(v<<(64*k) for k,v in enumerate(vals))
        for k,col in enumerate([0,3,8,9,10]):val|=(int(x[j,col])&0xffffffff)<<(256+32*k)
        val|=int(raw.ravel()[idx])<<416;val|=int(guarded.ravel()[idx])<<432;guards.append(f'{val:0112x}')
    (R/'sim/tb_compact_mlp.hex').write_text('\n'.join(mlp)+'\n')
    (R/'sim/tb_compact_guard.hex').write_text('\n'.join(guards)+'\n')
    ports=','.join(f'.p_read{str(i) if i else ""}(v[{32*i}+:32])' for i in range(40))
    (R/'sim/tb_compact_mlp.sv').write_text(tb('tb_compact_mlp','scalar_gain_predict',1296,ports,count,1280,15))
    ports=','.join(f'.{n}(v[{64*i}+:64])' for i,n in enumerate(['p','mx3','mx9','peak']))
    ports+=','+','.join(f'.p_read{str(i) if i else ""}(v[{256+32*i}+:32])' for i in range(5))+',.g(v[416+:15])'
    (R/'sim/tb_compact_guard.sv').write_text(tb('tb_compact_guard','scalar_gain_protect',448,ports,count,432,21))
    (R/'reports/rtl_vectors.json').write_text(json.dumps(dict(cases=count,guard_changed_cases=int(np.count_nonzero(raw.ravel()[chosen]!=guarded.ravel()[chosen])),mlp_unity_above=int(np.count_nonzero(g>16384))),indent=2))
    print('RTL_VECTORS_READY',count,flush=True)

if __name__=='__main__':main()
