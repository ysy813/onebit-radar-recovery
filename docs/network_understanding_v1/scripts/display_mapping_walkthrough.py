"""Read-only teaching audit of the existing power-to-display path.

Checks the table and existing integer mapper, traces FOUR ALREADY EXPLAINED
points, and demonstrates the existing byte display. No FFT, neural inference,
training, new holdout, hardware build or board access.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import re
import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
HW = ROOT / "radar1_scalar_compact_exp_v1"
LEGACY = ROOT / "radar1_v7_offline_compare_v1"
IP = HW / "ip_repo"

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def text(p):
    return p.read_text(encoding="utf-8-sig",errors="replace")

ccid = IP/"repo06_interp/interp_ip_1.0/src/CCID_count.v"
interp = IP/"repo06_interp/interp_ip_1.0/hdl/interp_ip_v1_0_M00_AXI.v"
scan = IP/"repo04_display/display_1.0/hdl/display_v1_0_M00_AXI.v"
video = IP/"repo05_hdmi_cam_picture4/src/video_display.v"
video_component = IP/"repo05_hdmi_cam_picture4/component.xml"
image_init = HW/"software/image_init.c"
table = HW/"software/aq_ar.bin"
bdpath=HW/"project/imaging_storage.srcs/sources_1/bd/design_1/design_1.bd"
plot = ROOT/"scalar_restore_v3/make_comparison.py"
trace_path=HERE/"reports/POINT_TRACE.json"
bd=read(bdpath)["design"]
assert bd["components"]["interp_ip_0"]["parameters"]["C_M00_AXI_BURST_LEN"]["value"]=="1"
assert bd["components"]["interp_ip_0"]["parameters"]["C_M00_AXI_DATA_WIDTH"]["value"]=="64"
assert bd["components"]["hdmi_picture2_0"]["vlnv"]=="xilinx.com:user:hdmi_picture2:1.0"
assert "<spirit:name>hdmi_picture2</spirit:name>" in text(video_component)
assert "radar_data_in[31:24]" in text(video)
assert "X_START=218,Y_START=149,WIDTH=844,HEIGHT=422" in text(video)
assert "wire keep_word=~column[0]" in text(scan)
assert "SOURCE_ROW_STEP=32'd26992" in text(scan)
assert "SOURCE_WIDTH=1687, OUTPUT_HEIGHT=422" in text(scan)
it=text(interp)
assert "DATA_FIND_out<=M_AXI_RDATA" in it and "axi_wdata<=DATA_FIND_out" in it
assert "DATA_FIND_addr < 32'h00400000" in it and "DATA_FIND_addr[2:0] == 3'b000" in it
assert "a[i]=UINT64_MAX" in text(image_init) and "b[i]=UINT64_MAX" in text(image_init)
pt=text(plot)
assert "vmin=-60,vmax=0,cmap='turbo'" in pt and "float(base.max())" in pt
active="\n".join(line.split("//")[0] for line in text(ccid).splitlines())
parameters={k:int(v,2) for k,v in re.findall(r"parameter\s+(\w+)\s*=\s*32'b([01]+)",active)}

# Load the EXISTING coordinate-only class; do not instantiate its network.
sys.path.insert(0,str(LEGACY))
spec=importlib.util.spec_from_file_location("existing_coordinate_mapper",LEGACY/"adapter.py")
old=importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
mapping=old.OriginalMapping()
assert sha(table)==sha(LEGACY/"reference/aq_ar.bin")
assert parameters==mapping.parameters
assert sha(ccid)==sha(LEGACY/"reference/CCID_count.v")

def address_from_current_constants(ar,aq):
    """Scalar transcription of the current CCID arithmetic, not float geometry."""
    mask31=(1<<31)-1
    neg=bool(aq & (1<<31))
    magq=((~aq)&mask31) if neg else aq
    xr=((magq*parameters["xr_par"])>>16)&mask31
    mid=((parameters["fa_new"]-xr) if neg else (parameters["fa_new"]+xr))&mask31
    xf=((mid*parameters["a"])>>16)&mask31
    xid=((xf>>16)+int(bool(xf&65535))+171)&65535
    magr=((~ar+1)&mask31) if neg else ar
    yf=((magr*parameters["yid_par"])>>16)&mask31
    yid=((yf>>16)+int(bool(yf&65535)))&65535
    return xid,yid,8*(xid+512*yid)

source_rows,source_cols=np.indices(mapping.index.shape)
preview=(source_rows%2==0)&(source_cols%2==0)
index=mapping.index[mapping.valid].astype("i8")
count=np.bincount(index,minlength=1024*512)
preview_count=np.bincount(mapping.index[mapping.valid&preview].astype("i8"),minlength=1024*512)
assert int(preview.sum())==844*422
pixels=[]
for rr,cc in [(0,0),(0,843),(210,422),(421,843),(422,844),(600,1000),(842,1686)]:
    ar,aq=int(mapping.ar[rr,cc]),int(mapping.aq[rr,cc])
    x,y,offset=address_from_current_constants(ar,aq)
    assert (x,y)==(int(mapping.xid[rr,cc]),int(mapping.yid[rr,cc]))
    assert offset==8*int(mapping.index[rr,cc])
    pixels.append(dict(output_row=rr,output_col=cc,ar_word=ar,aq_word=aq,
                       xid=x,yid=y,linear_byte_offset=offset,
                       geometry=bool(mapping.geometry[rr,cc]),
                       in_power_bank=offset<4*1024*1024,
                       retained_by_720p_decimation=bool(preview[rr,cc]),
                       scalar_matches_existing_mapper=True))

points=[]
for t in read(trace_path)["rows"]:
    r,a=t["natural_range_bin"],t["natural_doppler_bin"]
    shifted_a=a^256
    k=r*512+shifted_a
    locations=np.argwhere(mapping.valid&(mapping.index==k))
    visible=locations[(locations[:,0]%2==0)&(locations[:,1]%2==0)]
    pin=t["power"];g=t["final_gain_q14"]
    pout=min((1<<64)-1,(pin*g*g+(1<<27))>>28)
    assert pout==t["output_power"]
    points.append(dict(natural_index=[r,a],shifted_column=shifted_a,
        linear_index=k,power_address=f"0x{0x24000000+8*k:08X}",
        full_map_pixel_count=int(count[k]),preview_pixel_count=int(preview_count[k]),
        example_output_pixels=locations[:4].tolist(),
        example_screen_pixels=[[218+int(c)//2,149+int(rr)//2] for rr,c in visible[:4]],
        input_power=pin,output_power=pout,final_gain_q14=g,
        input_display_byte=(pin>>24)&255,output_display_byte=(pout>>24)&255,
        relative_power_db=10*math.log10(pout/pin) if pin and pout else None,
        existing_output_matches=True))

# Trace final stored outputs at a few pixels actually retained by scanout.
# These arrays are the ALREADY PUBLISHED diagnostic example, not new inference.
power_path=ROOT/"scalar_restore_v3/examples_compact/diagnosed_512_power.npy"
expected_path=power_path.with_name("diagnosed_512_expected.npz")
power=np.load(power_path,allow_pickle=False)
with np.load(expected_path,allow_pickle=False) as saved:
    final_gain=saved["gain_q14"].copy()
    final_power=saved["power"].copy()
preview_coords=np.argwhere(mapping.valid&preview)
memory_ids=mapping.index[mapping.valid&preview].astype("i8")
natural_r=memory_ids//512
natural_a=(memory_ids%512)^256
pp=power[natural_r,natural_a]
gg=final_gain[natural_r,natural_a]
selected=[]
for label,mask in [("retained_pixel_attenuated",gg<16384),("retained_pixel_unmodified",gg==16384)]:
    ids=np.flatnonzero(mask)
    assert len(ids)
    j=int(ids[np.argmax(pp[ids])])
    selected.append((label,j))
nearest=int(np.argmin(np.square(preview_coords-np.array([422,844])).sum(axis=1)))
selected.append(("retained_pixel_near_image_center",nearest))
visible_points=[]
for label,j in selected:
    rr,cc=[int(v) for v in preview_coords[j]]
    r,a=int(natural_r[j]),int(natural_a[j])
    pin=int(power[r,a]);g=int(final_gain[r,a]);pout=int(final_power[r,a])
    assert pout==min((1<<64)-1,(pin*g*g+(1<<27))>>28)
    visible_points.append(dict(label=label,source_image_row_col=[rr,cc],
        logical_screen_x_y=[218+cc//2,149+rr//2],natural_fft_index=[r,a],
        memory_column=a^256,power_byte_address=f"0x{0x24000000+8*int(memory_ids[j]):08X}",
        input_power=pin,final_gain_q14=g,final_gain=g/16384,output_power=pout,
        input_gray_byte=(pin>>24)&255,output_gray_byte=(pout>>24)&255,
        relative_power_db=10*math.log10(pout/pin) if pin and pout else None,
        stored_example_output_exact=True))

# A strict arithmetic counterexample for the CURRENT byte selector.
toy_in=1<<32;toy_gain=8192
toy_out=(toy_in*toy_gain**2+(1<<27))>>28
assert toy_out==1<<30 and ((toy_in>>24)&255)==0 and ((toy_out>>24)&255)==64
def pc_db(p,scale):
    return 20*math.log10(max(math.sqrt(p/scale),1e-12))
toy_db_in=pc_db(toy_in,toy_in);toy_db_out=pc_db(toy_out,toy_in)
assert abs(toy_db_out-toy_db_in+6.020599913279624)<1e-12

toy_reference=np.array([.2,.2]);toy_base=np.array([.3,.2]);toy_enhanced=np.array([.2,.28])
toy_multiplicity=np.array([1,4])
toy_b=(toy_base-toy_reference)**2;toy_e=(toy_enhanced-toy_reference)**2
weighted_demo=dict(rd_baseline_sse=float(toy_b.sum()),rd_enhanced_sse=float(toy_e.sum()),
    mapped_baseline_sse=float(toy_b@toy_multiplicity),mapped_enhanced_sse=float(toy_e@toy_multiplicity))
assert weighted_demo["rd_enhanced_sse"]<weighted_demo["rd_baseline_sse"]
assert weighted_demo["mapped_enhanced_sse"]>weighted_demo["mapped_baseline_sse"]
coherent_demo=dict(individual_powers=[1,1],same_phase_sum_power=abs(1+1)**2,
                   opposite_phase_sum_power=abs(1-1)**2)
assert coherent_demo["same_phase_sum_power"]==4 and coherent_demo["opposite_phase_sum_power"]==0

# Count multiplicities to explain the weighting implicit in mapped-pixel SSE.
assert int(count.sum())==int(mapping.valid.sum())
assert int(preview_count.sum())==int((mapping.valid&preview).sum())
generated=HW/"project/imaging_storage.gen/sources_1/bd/design_1/ipshared"
copies={
    ccid:generated/"c104/src/CCID_count.v",
    interp:generated/"c104/hdl/interp_ip_v1_0_M00_AXI.v",
    scan:generated/"f48a/hdl/display_v1_0_M00_AXI.v",
    video:generated/"8176/src/video_display.v",
}
copy_checks={str(p.relative_to(ROOT)):dict(path=str(c.relative_to(ROOT)),exists=c.is_file(),
    sha_equal=c.is_file() and sha(c)==sha(p)) for p,c in copies.items()}
assert all(v["exists"] and v["sha_equal"] for v in copy_checks.values()),copy_checks
result=dict(status="PASS",
    scope="Static coordinate/display arithmetic and four existing points; not a new imaging or quality test",
    table_bytes=table.stat().st_size,table_matches_existing_mapper=True,
    current_parameters=parameters,existing_parameter_and_ccid_match=True,
    actual_scalar_gather=dict(axi_data_width=64,axi_burst_len=1,multineighbor_weighting=False,
                             maximum_linear_offset_exclusive=4*1024*1024),
    map_summary=dict(width=1687,height=843,output_pixels=1687*843,
                     valid_pixels=int(mapping.valid.sum()),
                     outside_geometry_pixels=int((~mapping.geometry).sum()),
                     out_of_power_bank_pixels=int((mapping.geometry&~mapping.valid).sum()),
                     unique_power_words=int((count>0).sum()),max_reuse_of_one_power_word=int(count.max()),
                     preview_width=844,preview_height=422,preview_pixels=844*422,
                     preview_valid_pixels=int((mapping.valid&preview).sum()),
                     preview_unique_power_words=int((preview_count>0).sum()),
                     preview_source_row_step=2,preview_source_col_step=2,
                     screen_window_origin=[218,149]),
    pixel_address_checks=pixels,existing_points=points,existing_visible_pixel_traces=visible_points,
    byte_display=dict(formula="(power >> 24) & 255; repeat into R,G,B",monotone=False,
        counterexample=dict(input_power=toy_in,output_power=toy_out,amplitude_gain=.5,
                            input_byte=0,output_byte=64,input_db=toy_db_in,output_db=toy_db_out),
        skipped_pixels="No write; existing initialized display words retained. Initial UINT64_MAX appears white."),
    pc_display=dict(reference_scale="reference own frame peak",bypass_and_enhanced_scale="shared bypass frame peak",
                    scalar="20*log10(sqrt(power/scale))",limits_db=[-60,0],colormap="turbo",
                    coordinates="Natural range index and fftshifted Doppler FFT index; not Cartesian SAR coordinates"),
    mapped_metric_weighting_example=weighted_demo,coherent_phase_ambiguity_example=coherent_demo,
    generated_source_copies=copy_checks,
    source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ccid,interp,scan,video,video_component,image_init,table,bdpath,plot,trace_path,power_path,expected_path,LEGACY/"adapter.py"]},
    neural_parameters_modified=False,training_run=False,fft_run=False,feature_extraction_run=False,
    full_frame_neural_inference_run=False,new_quality_test_run=False,new_holdout_opened=False,
    hardware_built=False,board_accessed=False)
(HERE/"reports/DISPLAY_MAPPING_WALKTHROUGH.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(status=result["status"],map_summary=result["map_summary"],
    points=points,visible_pixels=visible_points,counterexample=result["byte_display"]["counterexample"],
    generated_copies_match=all(v["sha_equal"] for v in copy_checks.values())),ensure_ascii=False))
