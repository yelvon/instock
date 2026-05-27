#!/usr/bin/env bash
# 检查 Mac 本地通达信 vipdoc 是否齐全（拷完后 / 增量后运行）
set -euo pipefail

DST="${TDX_LOCAL_DST:-$HOME/tdx-local}"
SH="$DST/vipdoc/sh/lday"
SZ="$DST/vipdoc/sz/lday"

if [[ ! -d "$SH" ]]; then
  echo "FAIL: 未找到 $SH"
  echo "  请先在 Windows 虚拟机运行: scripts\\windows\\sync_tdx_to_mac.bat"
  exit 1
fi

sh_n=$(find "$SH" -name '*.day' 2>/dev/null | wc -l | tr -d ' ')
sz_n=$(find "$SZ" -name '*.day' 2>/dev/null | wc -l | tr -d ' ')
echo "本地目录: $DST"
echo "沪 .day: $sh_n"
echo "深 .day: $sz_n"

if [[ "$sh_n" -lt 4000 ]] || [[ "$sz_n" -lt 3500 ]]; then
  echo "WARN: 数量偏少，可能尚未全量同步或路径不对"
  exit 2
fi
HQ="$DST/T0002/hq_cache"
gbbq=""
for f in "$HQ/gbbq" "$HQ/gbbq.dat"; do
  if [[ -f "$f" ]]; then
    gbbq="$f"
    break
  fi
done
if [[ -n "$gbbq" ]]; then
  echo "gbbq: $gbbq ($(wc -c <"$gbbq" | tr -d ' ') bytes)"
elif [[ -d "$HQ" ]]; then
  echo "WARN: Mac 已有 hq_cache 但无 gbbq 主文件（仅有 map 或其它缓存不够）"
  echo "      hq_cache 示例: $(ls -1 "$HQ" 2>/dev/null | head -8 | tr '\n' ' ')"
  echo "      请在 Windows 通达信联网生成 gbbq 后重新 sync_tdx_to_mac.bat"
elif [[ ! -d "$DST/T0002" ]]; then
  echo "WARN: Mac 未同步 T0002（仅 vipdoc 时正常）— 请用更新后的 sync_tdx_to_mac.bat 再跑一遍"
else
  echo "WARN: 未找到 $HQ"
fi

echo "OK: 数量正常，可设置 INSTOCK_TDX_DIR_HOST=$DST 并 docker_dev_reload.sh"
exit 0
