"""活動來源。每個來源模組提供 NAME、LABEL、fetch(previous) -> bytes、parse(bytes, now) -> list[Event]。"""

from . import accupass, iculture, khcc, khh_travel, kmfa, kpmc, ksml, opentix, tixcraft, twmarket, weiwuying

# 順序也是去重合併時的優先順序：排前面的來源，其標題與欄位優先採用
SOURCES = [weiwuying, kpmc, ksml, khcc, kmfa, opentix, iculture, khh_travel, accupass, tixcraft, twmarket]
