# 深度登记 临床试验访视窗与方案锁库核验

规模：中型。使用者：临床试验数据管理员。核心规则：首访偏离入组基准时后续访视按实际首访重新起算，窗口、偏离与锁库共用同一锚点，入组基准窗仅留痕可追溯；方案修订按受试者生效时间选版；漏访不可用复检伪填。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 记录采信 | 执行并复核记录采信 | `POST /api/intake` | `app/modules/intake/rules.py` | `tests/test_intake.py` |
| M2 方案版本 | 执行并复核方案版本 | `POST /api/protocol` | `app/modules/protocol/rules.py` | `tests/test_protocol.py` |
| M3 排期锚点 | 裁决入组锚点或实际首访锚点 | `POST /api/anchor` | `app/modules/anchor/rules.py` | `tests/test_anchor.py` |
| M4 访视排窗 | 按锚点排窗并保留入组基准窗 | `POST /api/windows` | `app/modules/windows/rules.py` | `tests/test_windows.py` |
| M5 偏离复核 | 执行并复核偏离复核 | `POST /api/deviation` | `app/modules/deviation/rules.py` | `tests/test_deviation.py` |
| M6 复检裁决 | 执行并复核复检裁决 | `POST /api/retest` | `app/modules/retest/rules.py` | `tests/test_retest.py` |
| M7 锁库检查 | 执行并复核锁库检查 | `POST /api/locking` | `app/modules/locking/rules.py` | `tests/test_locking.py` |
| M8 冻结归档 | 执行并复核冻结归档 | `POST /api/archive` | `app/modules/archive/rules.py` | `tests/test_archive.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | 旧编码检验单位 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_legacy_real` |
| TRAP-02 | BOM表头 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_bom_real` |
| TRAP-08 | 受试者前导零 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_leading_zero_real` |
| TRAP-04 | 分段表头 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_header_real` |
| TRAP-05 | 缺列记录 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_columns_real` |
| TRAP-18 | 空态 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/intake/rules.py` | `tests/test_intake.py::test_empty_types` |
| TRAP-07 | 缺失检验值 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/protocol/rules.py` | `tests/test_protocol.py::test_sentinel_real` |
| TRAP-25 | 个体方案生效重叠 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/protocol/rules.py` | `tests/test_protocol.py::test_overlap_assignment` |
| TRAP-15 | 检验单位换算 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/protocol/rules.py` | `tests/test_protocol.py::test_unit_conversion_real` |
| TRAP-23 | 访视窗末端 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/windows/rules.py` | `tests/test_windows.py::test_half_open_end` |
| TRAP-11 | UTC日历归一 | 静默错算或证据丢失 | 以可复核规则显式处理 | `app/modules/windows/rules.py` | `tests/test_windows.py::test_utc_day_equivalence` |
| TRAP-26 | 首访推迟后的双口径窗口 | 入组基准与实际首访各算一套，锁库口径分裂 | 裁决单一锚点：后续访视按实际首访重锚，窗口/偏离/锁库共用；入组基准窗仅 baseline_* 留痕，首访偏离保留不被重算消除 | `app/modules/anchor/rules.py`、`app/modules/windows/rules.py` | `tests/test_anchor.py` |

## 对账规则

原始逻辑输入=采纳行+隔离行+空行+重复表头+同值重复。业务计算按 DATA-DICTIONARY.md 分别核验，不能把上级与下级重复加总。所有隔离保留编号、原值、原始行号和稳定原因码。锚点口径与入组基准口径同屏可追溯，但阻断只按锚点口径计一次，禁止双口径重复加总。

## 已知不覆盖

数据来自仓内样例或用户粘贴文件，不连接外部业务生产系统。平台不执行实际资金划转或行政审批。
