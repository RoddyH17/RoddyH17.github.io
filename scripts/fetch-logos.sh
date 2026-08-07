#!/bin/bash
# 抓取 protocol logo 到 public/logos/ —— 只跑一次,不是构建步骤。
#
# 用法: ./scripts/fetch-logos.sh
#
# 为什么下载到本地而不是外链图床:这是静态站,浏览时不该依赖第三方。
# 图床挂了或者限流,整面卡片墙就空了。
#
# 来源是 DefiLlama 的 icon CDN。它的 slug 和我们 protocols.yaml 里的 id
# 不一定同名(curve 在那边叫 curve-dex),而且公链走 /chains/ 路径不走
# /protocols/,所以这里显式写一张映射表,不靠猜。
set -e
cd "$(dirname "$0")/.."

OUT=public/logos
mkdir -p "$OUT"

# id|类型(protocols|chains)|DefiLlama slug
MAP='
uniswap|protocols|uniswap
curve|protocols|curve-dex
balancer|protocols|balancer
raydium|protocols|raydium
orca|protocols|orca
meteora|protocols|meteora
aave|protocols|aave
compound|protocols|compound-finance
kamino|protocols|kamino-lend
hyperliquid|protocols|hyperliquid
gmx|protocols|gmx
drift|protocols|drift-trade
ethereum|chains|rsz_ethereum
solana|chains|rsz_solana
arbitrum|chains|rsz_arbitrum
'

fail=0
echo "$MAP" | while IFS='|' read -r id kind slug; do
  [ -z "$id" ] && continue
  url="https://icons.llamao.fi/icons/${kind}/${slug}?w=128&h=128"
  code=$(curl -s -o "$OUT/${id}.webp" -w '%{http_code}' --max-time 20 "$url" || echo 000)
  size=$(wc -c < "$OUT/${id}.webp" | tr -d ' ')
  # CDN 对未知 slug 也返回 200 + 一张占位图,所以用体积做二次判断
  if [ "$code" != "200" ] || [ "$size" -lt 500 ]; then
    echo "⚠️  ${id}: HTTP ${code}, ${size} bytes — 检查 slug: ${url}"
    fail=1
  else
    echo "✅ ${id}.webp (${size} bytes)"
  fi
done

echo ""
echo "存放在 ${OUT}/ 。protocols.yaml 里的 logo: 字段指向这里。"
