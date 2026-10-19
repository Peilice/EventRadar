"""活動來源。每個來源模組提供 NAME、LABEL、fetch() -> bytes、parse(bytes, now) -> list[Event]。"""

from . import iculture, khh_travel, kktix

# 順序也是去重合併時的優先順序：排前面的來源，其標題與欄位優先採用
SOURCES = [iculture, khh_travel, kktix]
