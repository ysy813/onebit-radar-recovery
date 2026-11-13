from pathlib import Path
import hashlib
import json
from PIL import Image

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parents[1]
ASSETS = WORK / '.build' / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
sources = {}

def crop(source, name, box):
    path = ROOT / source
    image = Image.open(path).convert('RGB')
    image.crop(box).save(ASSETS / name)
    sources[name] = dict(source=source, crop=list(box), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

# Existing, audited scientific figures. Crops retain the quantities they show.
crop('network_understanding_v1/figures/08_network_architecture.png', 'inference.png', (55, 115, 3230, 1090))
crop('network_understanding_v1/figures/08_network_architecture.png', 'training.png', (55, 1200, 3230, 1635))
# Remove only the disconnected remnants of the cross-panel training connector.
# The source figure remains unchanged, and all boxes and inference arrows remain.
for name, box in [('inference.png', (1540, 650, 1625, 975)),
                  ('training.png', (2520, 0, 2640, 25))]:
    asset = Image.open(ASSETS / name).convert('RGB')
    asset.paste('white', box)
    asset.save(ASSETS / name)
    sources[name]['connector_cleanup'] = list(box)
crop('network_understanding_v1/figures/05_feature_layout.png', 'neighbors.png', (0, 0, 858, 884))
crop('network_understanding_v1/figures/01_sign_harmonics.png', 'harmonics.png', (0, 0, 2216, 758))
crop('network_understanding_v1/figures/02_alias_coordinates.png', 'alias.png', (0, 0, 1604, 974))
source = 'scalar_restore_v3/results_compact/images/compact_synth_128001_512.png'
crop(source, 'rd-reference.png', (0, 33, 743, 660))
crop(source, 'rd-bypass.png', (750, 33, 1492, 660))
crop(source, 'rd-compact.png', (750, 670, 1492, 1298))
crop(source, 'rd-colorbar.png', (1520, 33, 1690, 1298))
colorbar = Image.open(ASSETS / 'rd-colorbar.png')
colorbar.crop((26, 31, 85, 1207)).save(ASSETS / 'rd-colorbar-strip.png')

evidence = json.loads((ROOT / 'network_understanding_v1/reports/EVIDENCE_WALKTHROUGH.json').read_text(encoding='utf-8'))
config = json.loads((ROOT / 'scalar_restore_v3/pc_candidate_compact/config.json').read_text(encoding='utf-8'))
result = json.loads((ROOT / 'scalar_restore_v3/RESULTS_COMPACT.json').read_text(encoding='utf-8'))
assert config['network'] == [40, 32, 16, 1] and config['parameters'] == 1857
assert evidence['quality_status_preserved'] == 'FAIL'
assert result['full_original_quality_status'] == 'FAIL'
assert result['neural_weights_changed'] is False

baseline = json.loads((ROOT / 'network_understanding_v1/reports/SOURCE_BASELINE.json').read_text(encoding='utf-8'))
frozen = {}
for relative, item in baseline.items():
    current = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    assert current == item['sha256'], relative
    frozen[relative] = current

(WORK / '.build' / 'facts.json').write_text(json.dumps(dict(
    assets=sources, groups=evidence['groups'], known_targets=evidence['known_target_summary'],
    result=result, frozen_sources=frozen,
), ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(status='PASS', frozen_sources=len(frozen), assets=len(sources)), ensure_ascii=False))
