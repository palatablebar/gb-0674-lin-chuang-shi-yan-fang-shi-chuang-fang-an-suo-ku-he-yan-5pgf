from app.modules.anchor.rules import build_anchors
from app.modules.windows.rules import calculate
from copy import deepcopy

def test_clean_keeps_enrollment_anchor(clean):
    anchors = clean['anchors']
    assert len(anchors) == 20
    assert all(a['anchor_source'] == 'ENROLLMENT' for a in anchors.values())
    assert all(a['shift_days'] == 0 for a in anchors.values())
    assert clean['balance']['reanchored_subjects'] == 0

def test_dirty_reanchors_late_first_visit(sample):
    anchor = sample['anchors']['00001']
    assert anchor['anchor_source'] == 'ACTUAL_FIRST'
    assert anchor['anchor_date'] == '2026-10-12'
    assert anchor['enrolled_date'] == '2026-10-01'
    assert anchor['shift_days'] == 11
    assert anchor['baseline_code'] == 'LATE'
    assert sample['balance']['reanchored_subjects'] == 1

def test_first_visit_deviation_preserved_under_anchor(sample):
    # 首访始终按入组基准评判，偏离留痕，复检不能消除；重锚不改写首访判定
    v1 = next(r for r in sample['windows'] if r['id'] == '00001-V1')
    assert v1['baseline_code'] == 'LATE' and v1['code'] == 'LATE' and v1['day'] == 11
    assert any(d['id'] == '00001-V1' and d['code'] == 'WINDOW_LATE' for d in sample['deviations'])

def test_followup_window_uses_actual_anchor(sample):
    # V2 在入组基准下窗外（day14 已过 v2 窗 [13,18)? 实际入组日差14在窗内；锚点日差3 → 窗外 EARLY）
    v2 = next(r for r in sample['windows'] if r['id'] == '00001-V2')
    assert v2['anchor_source'] == 'ACTUAL_FIRST'
    assert v2['day'] == 3
    assert v2['code'] == 'EARLY'
    assert v2['baseline_day'] == 14 and v2['baseline_code'] == 'IN_WINDOW'

def test_missing_first_visit_falls_back_to_enrollment(sample):
    anchor = sample['anchors']['00020']
    assert anchor['anchor_source'] == 'ENROLLMENT'
    assert anchor['first_visit_id'] == '00020-V1'
    # 00020 有 V1 但缺 V2：V1 在窗，沿用入组锚点；缺访视由偏离模块记 MISSING_PRIMARY
    assert any(d['subject'] == '00020' and d['code'] == 'MISSING_PRIMARY' for d in sample['deviations'])

def test_duplicate_first_visit_blocks_reanchor(clean):
    records = clean['records'] + [dict(clean['records'][0], id='DUP-V1')]
    anchors = build_anchors(records, clean['context'])
    entry = anchors['00001']
    assert entry['anchor_source'] == 'ENROLLMENT'
    assert '重复' in entry['first_visit_status']

def test_early_first_visit_reanchors_backward(clean):
    records = [dict(r) for r in clean['records']]
    first = next(r for r in records if r['id'] == '00002-V1')
    first['at'] = '2026-10-04T08:00:00+08:00'  # 入组日差3，v1 窗 [5,10) → EARLY
    anchors = build_anchors(records, clean['context'])
    entry = anchors['00002']
    assert entry['anchor_source'] == 'ACTUAL_FIRST'
    assert entry['anchor_date'] == '2026-10-04'
    assert entry['shift_days'] == 3
    assert entry['baseline_code'] == 'EARLY'

def test_calculate_without_anchors_defaults_enrollment(clean):
    row = clean['records'][0]
    result = calculate(row, clean['context'])
    assert result['anchor_source'] == 'ENROLLMENT'
    assert result['day'] == result['baseline_day'] == 7
    assert result['code'] == result['baseline_code'] == 'IN_WINDOW'

def test_windows_carry_both_calendars(clean):
    row = clean['windows'][0]
    for key in ('anchor_source', 'anchor_date', 'shift_days', 'baseline_day',
                'baseline_start_day', 'baseline_end_day', 'baseline_code'):
        assert key in row

def test_single_anchor_no_second_blocking_calendar(sample):
    # 偏离只按锚点口径生成；入组基准窗仅留痕，不产生第二套阻断
    v2_issue = [d for d in sample['deviations'] if d.get('id') == '00001-V2']
    assert v2_issue and v2_issue[0]['code'] == 'WINDOW_EARLY'
    assert all('baseline' not in d['code'] for d in sample['deviations'])
