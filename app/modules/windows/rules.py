from datetime import timezone, timedelta, date
from app.coerce import instant

ZONE = timezone(timedelta(hours=8))

def _day(value):
    if isinstance(value, date):
        return value
    text = str(value)
    if len(text) == 10:  # 锚点/入组日期：Asia/Shanghai 日历日，无时序偏移
        return date.fromisoformat(text)
    return instant(text).astimezone(ZONE).date()

def _code(day, start, end):
    return 'IN_WINDOW' if start <= day < end else ('EARLY' if day < start else 'LATE')

def calculate(row, context, anchors=None):
    start, end = context['plans'][row['selected_protocol']][row['visit']]
    enrolled_day = _day(row['enrolled'])
    baseline_day = (_day(row['at']) - enrolled_day).days
    baseline_code = _code(baseline_day, start, end)
    anchor = (anchors or {}).get(row['subject'])
    if anchor is None:
        anchor_source, anchor_date, shift_days = 'ENROLLMENT', enrolled_day.isoformat(), 0
    else:
        anchor_source, anchor_date, shift_days = anchor['anchor_source'], anchor['anchor_date'], anchor['shift_days']
    is_first_visit = bool(anchor) and row['visit'] == anchor.get('first_visit', 'V1')
    if is_first_visit:
        # 首访始终按入组基准评判：它的偏离是重锚触发原因，不得因重锚被改写
        day, code = baseline_day, baseline_code
    else:
        day = (_day(row['at']) - _day(anchor_date)).days
        code = _code(day, start, end)
    return {
        'id': row['id'], 'subject': row['subject'], 'visit': row['visit'], 'kind': row['kind'],
        'day': day, 'start_day': start, 'end_day': end,
        'selected_protocol': row['selected_protocol'], 'code': code,
        'anchor_source': anchor_source, 'anchor_date': anchor_date, 'shift_days': shift_days,
        'baseline_day': baseline_day, 'baseline_start_day': start, 'baseline_end_day': end,
        'baseline_code': baseline_code, 'line': row['_line'],
    }

def apply(state):
    state['windows'] = [calculate(r, state['context'], state.get('anchors')) for r in state['records']]
    primary = [r for r in state['windows'] if r['kind'] == 'PRIMARY']
    state['views']['windows'] = {
        'title': '访视窗口',
        'rows': state['windows'],
        'metrics': {
            '首次访视': len(primary),
            '窗内': sum(r['code'] == 'IN_WINDOW' for r in primary),
            '窗外': sum(r['code'] != 'IN_WINDOW' for r in primary),
            '重锚受试者': sum(a['anchor_source'] == 'ACTUAL_FIRST' for a in state.get('anchors', {}).values()),
        },
    }
