"""Freeze the conservative correction before generating any fresh-test pair."""
from experiment import ROOT,read,write,sha

report=read(ROOT/'development_profiled/report.json');acceptance=read(ROOT/'CORRECTION_ACCEPTANCE.json')
checks={k:report['summary']['checks'][k] for k in acceptance['checks']}
row=next(r for r in report['rows'] if r['id']=='confirm_synth_116013_512')
diagnosed=next(t for t in row['targets'] if t['measured_peak_bin']==[221,205])
checks['diagnosed_target_no_longer_below_half']=diagnosed['enhanced_retention']>=.5
result=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,diagnosed_target=diagnosed,original_full_quality_status=report['status'],original_full_quality_checks=report['summary']['checks'],scope='User-requested weak-target correction; not a replacement of full quality verdict')
write(ROOT/'DEVELOPMENT_CORRECTION_CHECK.json',result)
if not all(checks.values()):raise RuntimeError('Correction acceptance failed on development data; no test-set selection permitted')
frozen=dict(status='WEAK_CORRECTION_FROZEN_REQUIRES_FRESH_TEST',path=report['model_path'],sha256=report['model_sha256'],development_report='development_profiled/report.json',development_correction='PASS',development_original_full_quality=report['status'],protocol_sha256=sha(ROOT/'EXPERIMENT_PROTOCOL.json'),correction_acceptance_sha256=sha(ROOT/'CORRECTION_ACCEPTANCE.json'),profile_policy_sha256=sha(ROOT/'PROFILE_POLICY.json'),test_not_read=True,ip_built=False,bit_rebuilt=False,board_accessed=False)
assert sha(frozen['path'])==frozen['sha256']
if (ROOT/'FROZEN_MODEL.json').exists():raise FileExistsError(ROOT/'FROZEN_MODEL.json')
write(ROOT/'FROZEN_MODEL.json',frozen)
print(result,flush=True)
