from pathlib import Path
import hashlib
import json
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent / 'radar1_scalar_compact_exp_v1'
PKG = ROOT / 'pkg'
EXPECTED_BIT = 'f884d829c217130fb930f85f78019975b1f5d4263f4dd38a482f73ef0d3d73cb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    save(PKG / 'BUILD_READY.json', {'ready_for_board_test': False, 'reason': 'checks in progress'})
    snapshot = json.loads((ROOT / 'reports/original_snapshot.json').read_text(encoding='utf-8-sig'))
    for entry in snapshot:
        assert sha(Path(entry['Path'])) == entry['SHA256'], entry['Path']
    assert sha(PKG / 'design_1_wrapper.bit') == EXPECTED_BIT
    assert sha(PKG / 'psu_init.tcl') == sha(PARENT / 'pkg/psu_init.tcl')
    assert sha(ROOT / 'tests/vendor/ff.c') == sha(PARENT / 'vitis/scalar/psu_cortexa53_0/standalone_domain/bsp/psu_cortexa53_0/libsrc/xilffs_v4_7/src/ff.c')
    for name in ('aq_ar.bin', 'image_init.c', 'branch_control.h', 'network_monitor.h', 'lscript.ld'):
        assert sha(ROOT / 'software' / name) == sha(PARENT / 'software' / name), name
    original_bsp = PARENT / 'vitis/scalar/export/scalar/sw/scalar/standalone_domain'
    for path in (ROOT / 'bsp/include').rglob('*'):
        if path.is_file():
            assert sha(path) == sha(original_bsp / 'bspinclude/include' / path.relative_to(ROOT / 'bsp/include'))
    for name in ('libxil.a', 'libxilffs.a'):
        assert sha(ROOT / 'bsp/lib' / name) == sha(original_bsp / 'bsplib/lib' / name)
    log = (ROOT / 'reports/fatfs_regression.log').read_text(encoding='utf-8-sig')
    cases = re.findall(r'^CASE_PASS (.+)$', log, re.M)
    assert len(cases) == 7 and 'FATFS_REGRESSION_PASS cases=7' in log
    assert (ROOT / 'software/sd_space.c').stat().st_mtime <= (ROOT / 'test_build/sd_space.o').stat().st_mtime
    assert (ROOT / 'software/sd_space.c').stat().st_mtime <= (PKG / 'onebit_network_storage.elf').stat().st_mtime
    assert (ROOT / 'software/radar_sd_long.c').stat().st_mtime <= (PKG / 'onebit_network_storage.elf').stat().st_mtime

    data = (PKG / 'onebit_network_storage.elf').read_bytes()
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    assert h[0][:6] == b'\x7fELF\x02\x01' and h[2] == 183, 'ELF must be little-endian AArch64'
    end = 0
    for i in range(h[10]):
        p = struct.unpack_from('<IIQQQQQQ', data, h[5] + i * h[9])
        if p[0] == 1 and p[6]:
            assert all(0x100000 <= a and a + p[6] <= 0x02000000 for a in (p[3], p[4]))
            end = max(end, p[3] + p[6])
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, h[6] + i * h[11]) for i in range(h[12])]
    symbols = set()
    table_ok = False
    for s in sections:
        if s[1] != 2:
            continue
        st = sections[s[6]]
        strings = data[st[4]:st[4] + st[5]]
        for off in range(s[4], s[4] + s[5], s[9]):
            n, _, _, index, address, _ = struct.unpack_from('<IBBHQQ', data, off)
            name = strings[n:strings.find(b'\0', n)].decode(errors='replace')
            symbols.add(name)
            if name == '_binary_aq_ar_bin_start':
                sec = sections[index]
                begin = sec[4] + address - sec[3]
                table_ok = data[begin:begin + 11377128] == (ROOT / 'software/aq_ar.bin').read_bytes()
    assert table_ok
    assert {'f_mount', 'f_getfree', 'f_write', 'f_sync', 'sd_prepare_space', 'XAxiDma_CfgInitialize'} <= symbols
    for message in (b'radar1-scalar-compact-sd-fix-v1', b'SD_SCAN:', b'SD_SPACE_PASS:', b'SD_MANIFEST_PASS:', b'SD_FSINFO_STALE:', b'NETWORK_REQUEST=%u'):
        assert message in data, message
    source = (ROOT / 'software/radar_sd_long.c').read_text()
    body = source[source.index('int main(void)'):]
    assert body.index('sd_prepare_space(') < body.index('make_manifest()') < body.index('enable_capture_mode(')
    assert 'FA_WRITE|FA_CREATE_NEW' in source
    origin_source = (PARENT / 'software/radar_sd_long.c').read_text()
    for function, following in [('store_block', 'verify_files'), ('verify_files', None)]:
        pattern = rf'static int {function}\(.*?(?=\nstatic int {following}\()' if following else rf'static int {function}\(.*?(?=\nint main\()'
        assert re.search(pattern, source, re.S)[0] == re.search(pattern, origin_source, re.S)[0]

    parent_ready = json.loads((PARENT / 'pkg/BUILD_READY.json').read_text(encoding='utf-8'))
    checks = {
        'status': 'PASS', 'regression_cases': cases,
        'original_package_and_software_unchanged': True,
        'original_bit_reused_exactly': True, 'psu_init_unchanged': True,
        'bsp_headers_and_libraries_unchanged': True,
        'raw_store_and_readback_functions_unchanged': True,
        'elf_aarch64': True, 'elf_load_end_exclusive': f'0x{end:08x}',
        'aq_ar_exact': True, 'startup_scan_before_dma_and_network': True,
        'board_tested': False, 'physical_card_modified_by_agent': False,
    }
    save(ROOT / 'reports/STANDARD_CHECK.json', checks)
    save(ROOT / 'BUILD_STATUS.json', {
        'stage': 'SOFTWARE_SD_FIX_READY_FOR_BOARD_TEST', 'issue': 'SD-START-001',
        'physical_root_cause_confirmed_read_only': True,
        'software_build': 'PASS', 'fatfs_regression': 'PASS', 'standard_checks': 'PASS',
        'bitstream_rebuilt': False, 'original_sources_modified': False,
        'board_tested': False, 'quality_certified': False,
        'full_system_timing_signoff': False,
    })
    names = ('design_1_wrapper.bit', 'psu_init.tcl', 'onebit_network_storage.elf',
             'program_onebit_network_storage.tcl', 'program_common.tcl', '修复说明与操作步骤.md')
    hashes = {name: sha(PKG / name) for name in names}
    (PKG / 'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name, digest in hashes.items()), encoding='utf-8')
    save(PKG / 'BUILD_READY.json', {
        'revision': ROOT.name, 'ready_for_board_test': True, 'board_tested': False,
        'experimental': True, 'quality_certified': False,
        'upstream_overall_quality_status': 'FAIL', 'parent_revision': PARENT.name,
        'software_issue': 'SD-START-001', 'hardware_signature': '0x71',
        'hardware_rebuilt': False, 'hardware_bit_sha256': EXPECTED_BIT,
        'mode': 'onebit_network_storage', 'control_word': 15,
        'model': parent_ready['model'], 'model_weights_sha256': parent_ready['model_weights_sha256'],
        'storage_always_raw': True, 'full_system_timing_signoff': False,
        'inherited_timing': parent_ready['timing'],
        'software_validation': checks, 'sha256': hashes,
    })
    print('SD_FIX_RELEASE_PASS')


if __name__ == '__main__':
    main()
