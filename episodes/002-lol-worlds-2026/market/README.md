# 冻结后市场取价记录

本版AI文件于北京时间2026年11月10日14:09:44冻结，随后在14:11:55取得Polymarket整场Match Winner（marketId6889027）的报价。GEN买一/卖一0.62/0.63，中间价62.5%；BLG为0.37/0.38，中间价37.5%，未归一化，Gamma和两本订单簿一致。AI66.5/33.5相对中间价的显示差为±4.0个百分点。

来源：https://polymarket.com/event/lol-blg-gen-2026-11-14 。这是整场胜者，不是单局或让局。原合约取消/平局按50–50，延期起始期限为2026年11月28日23:59 ET，并受已公告改期条款约束；弃权、来源规则也不同。因此只有在合约有效期内正常完赛时比较同一胜者，不能当作完全相同条件的精确概率差。

公开JSON移除了本机predictionFile绝对路径，原文件SHA和公开SHA见public-export.json；冻结概率文件本身未改。该市场快照不参与预测调参，也不证明谁更准。此处的报价是历史快照，不是实时价。GitHub实际公开时间以Release published_at为准，不能用本地冻结时间代替。

comparison-audit.json为独立本地核对；scope-clarification.zh.md补充有效期口径。BLG/GEN的原始中间价和订单簿JSON随包提供；完整合约正文、网页和API事件响应不再分发。
