"""PC CLI using only observed I/Q signs and one-bit FFT power."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import argparse
from experiment_v2 import ROOT, CFG, MODEL, read, write, sha, np, ENGINE, load_model, gain_float, guarded_gain, outputs, source_digests
import solver

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.json').exists():
        raise FileExistsError(a.output)
    frozen = read(ROOT/'FROZEN.json')
    assert frozen['sources'] == source_digests()
    assert frozen['model_sha256'] == sha(MODEL)
    with np.load(a.input, allow_pickle=False) as d:
        si, sq, base = d['sign_i'], d['sign_q'], d['base']
    if base.shape != (1024, 512) or base.dtype != np.dtype('u8'):
        raise ValueError('Expected uint64 1024x512 power')
    x = np.sqrt(base.astype('f8')); x = (x/max(x.max(), 1)).astype('f4')
    f = ENGINE.features(base)
    old = x*guarded_gain(base, gain_float(load_model(MODEL, 40), f), f)
    model, sr = solver.solve(si, sq, {**CFG['solver'], 'strategy':'residual24'})
    combined, evidence = outputs(x, old, model, sr, [frozen['alpha']])
    out = dict(old40=old, residual24_model=model)
    out.update({'residual24_'+k:v for k,v in combined.items()})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.output, **out)
    write(a.output.with_suffix('.json'), dict(solver=sr, evidence=evidence,
        input_sha256=sha(a.input), output_sha256=sha(a.output),
        frozen_sha256=sha(ROOT/'FROZEN.json'), deployment_ready=False))
    print('推理完成：只读取I/Q符号与单比特功率，未读取真值或多比特参考。')

if __name__ == '__main__': main()
