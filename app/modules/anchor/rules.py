from collections import defaultdict
from datetime import timezone, timedelta, date
from app.coerce import instant

ZONE = timezone(timedelta(hours=8))
FIRST_VISIT = 'V1'

def _day(value):
    if isinstance(value, date):
        return value
    return instant(value).astimezone(ZONE).date()

def _enrollment_window(row, context):
    """入组基准（旧锚点）下首访的半开窗，用于判定首访是否偏离及证据留存。"""
    start, end = context['plans'][row['selected_protocol']][row['visit']]
    day = (_day(row['at']) - _day(row['enrolled'])).days
    code = 'IN_WINDOW' if start <= day < end else ('EARLY' if day < start else 'LATE')
    return day, start, end, code

def build_anchors(records, context):
    """逐受试者裁决排期锚点：首访唯一且偏离入组基准窗时，以实际首访日重锚。"""
    primary = defaultdict(list)
    for row in records:
        if row['kind'] == 'PRIMARY':
            primary[(row['subject'], row['visit'])].append(row)
    anchors = {}
    for subject in sorted(context['subjects']):
        enrolled = _day(context['subjects'][subject])
        first = primary.get((subject, FIRST_VISIT), [])
        entry = {
            'subject': subject,
            'anchor_source': 'ENROLLMENT',
            'anchor_date': enrolled.isoformat(),
            'enrolled_date': enrolled.isoformat(),
            'shift_days': 0,
            'first_visit': FIRST_VISIT,
            'first_visit_id': '',
            'first_visit_status': '缺失或重复，未重锚',
            'baseline_day': '',
            'baseline_start_day': '',
            'baseline_end_day': '',
            'baseline_code': '',
        }
        if len(first) != 1:
            anchors[subject] = entry
            continue
        row = first[0]
        day, start, end, code = _enrollment_window(row, context)
        anchor_day = _day(row['at'])
        entry.update({
            'first_visit_id': row['id'],
            'baseline_day': day,
            'baseline_start_day': start,
            'baseline_end_day': end,
            'baseline_code': code,
        })
        if code == 'IN_WINDOW':
            entry['first_visit_status'] = '首访在窗，沿用入组锚点'
            anchors[subject] = entry
            continue
        # 首访提前或推迟：后续访视从实际首访重新起算，首访偏离本身仍留痕
        entry.update({
            'anchor_source': 'ACTUAL_FIRST',
            'anchor_date': anchor_day.isoformat(),
            'shift_days': (anchor_day - enrolled).days,
            'first_visit_status': '首访' + ('推迟' if code == 'LATE' else '提前') + '，按实际首访重锚',
        })
        anchors[subject] = entry
    return anchors

def apply(state):
    state['anchors'] = build_anchors(state['records'], state['context'])
    rows = list(state['anchors'].values())
    shifted = [r for r in rows if r['anchor_source'] == 'ACTUAL_FIRST']
    state['views']['anchor'] = {
        'title': '排期锚点裁决',
        'rows': rows,
        'metrics': {
            '受试者': len(rows),
            '实际首访重锚': len(shifted),
            '沿用入组锚点': len(rows) - len(shifted),
        },
    }
