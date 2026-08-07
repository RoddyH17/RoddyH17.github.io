#!/bin/bash
# DeepWiki 检索客户端 —— research 管道的「检索层」
#
# 用法:
#   ./scripts/deepwiki.sh structure <repo>
#   ./scripts/deepwiki.sh contents  <repo>
#   ./scripts/deepwiki.sh ask       <repo> "<问题>" [--note <mdx 路径>]
#
# 例:
#   ./scripts/deepwiki.sh structure Uniswap/v2-core
#   ./scripts/deepwiki.sh ask Uniswap/v2-core "How is the 0.3% fee encoded in the K check?" \
#       --note src/content/research/uniswap/amm-v2-lp.mdx
#
# 带 --note 时,除了打印答案,还会把这次提问和 DeepWiki 的永久检索链接
# 追加进那篇笔记 frontmatter 的 deepwiki: 列表 —— 检索轨迹自动留痕。
#
# 注意: DeepWiki 是检索层,不是结论层。它答出来的东西必须回原始源码
# 核对 commit 和行号再写进笔记(它确实会答错——v2 的乐观转账顺序就答反了)。
set -e
cd "$(dirname "$0")/.."

URL=https://mcp.deepwiki.com/mcp
ACCEPT='application/json, text/event-stream'

cmd="${1:?用法: ./scripts/deepwiki.sh <structure|contents|ask> <repo> [问题] [--note 路径]}"
repo="${2:?缺少 repo,例: Uniswap/v2-core}"

case "$cmd" in
  structure) tool=read_wiki_structure; args=$(python3 -c "import json,sys;print(json.dumps({'repoName':sys.argv[1]}))" "$repo") ;;
  contents)  tool=read_wiki_contents;  args=$(python3 -c "import json,sys;print(json.dumps({'repoName':sys.argv[1]}))" "$repo") ;;
  ask)
    question="${3:?ask 需要一个问题}"
    tool=ask_question
    args=$(python3 -c "import json,sys;print(json.dumps({'repoName':sys.argv[1],'question':sys.argv[2]}))" "$repo" "$question")
    ;;
  *) echo "❌ 未知命令: $cmd (可用: structure / contents / ask)"; exit 1 ;;
esac

note=""
[ "$4" = "--note" ] && note="$5"

# --- MCP streamable-HTTP 握手 ---------------------------------------------
hdrs=$(mktemp)
curl -s -D "$hdrs" -o /dev/null --max-time 30 -X POST "$URL" \
  -H "Content-Type: application/json" -H "Accept: $ACCEPT" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"research-pipeline","version":"1"}}}'
sid=$(grep -i '^mcp-session-id:' "$hdrs" | tr -d '\r' | awk '{print $2}')
rm -f "$hdrs"
SH=(); [ -n "$sid" ] && SH=(-H "Mcp-Session-Id: $sid")

curl -s -o /dev/null --max-time 30 -X POST "$URL" \
  -H "Content-Type: application/json" -H "Accept: $ACCEPT" "${SH[@]}" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

body=$(python3 -c "
import json,sys
print(json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/call',
  'params':{'name':sys.argv[1],'arguments':json.loads(sys.argv[2])}}))
" "$tool" "$args")

out=$(mktemp)
curl -s --max-time 300 -X POST "$URL" \
  -H "Content-Type: application/json" -H "Accept: $ACCEPT" "${SH[@]}" \
  -d "$body" \
| python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('data:'):
        continue
    try:
        msg = json.loads(line[5:].strip())
    except Exception:
        continue
    if 'error' in msg:
        print('ERROR:', json.dumps(msg['error'])[:600]); break
    for c in msg.get('result', {}).get('content', []):
        if c.get('type') == 'text':
            print(c['text'])
" | tee "$out"

# --- 把检索轨迹写回笔记 frontmatter ---------------------------------------
if [ -n "$note" ] && [ "$cmd" = "ask" ]; then
  python3 - "$note" "$repo" "$question" "$out" <<'PY'
import json, re, sys, datetime

note_path, repo, question, out_path = sys.argv[1:5]
answer = open(out_path).read()

m = re.search(r'https://deepwiki\.com/search/\S+', answer)
if not m:
    print('\n⚠️  答案里没找到 DeepWiki 永久链接,未写入 frontmatter')
    sys.exit(0)
url = m.group(0).rstrip('.,)')

src = open(note_path).read()
if not src.startswith('---'):
    print(f'\n⚠️  {note_path} 没有 frontmatter,未写入')
    sys.exit(0)

end = src.index('\n---', 3)
fm, rest = src[:end], src[end:]

if url in fm:
    print('\n✓ 这条检索已在 frontmatter 里,跳过')
    sys.exit(0)

entry = (
    f"\n  - repo: {json.dumps(repo)}\n"
    f"    question: {json.dumps(question)}\n"
    f"    url: {json.dumps(url)}\n"
    f"    date: {json.dumps(datetime.date.today().isoformat())}"
)

if re.search(r'^deepwiki:\s*\[\s*\]\s*$', fm, re.M):
    fm = re.sub(r'^deepwiki:\s*\[\s*\]\s*$', 'deepwiki:' + entry, fm, count=1, flags=re.M)
elif re.search(r'^deepwiki:\s*$', fm, re.M):
    fm = re.sub(r'^deepwiki:\s*$', 'deepwiki:' + entry, fm, count=1, flags=re.M)
else:
    fm = fm.rstrip('\n') + '\ndeepwiki:' + entry + '\n'

open(note_path, 'w').write(fm + rest)
print(f'\n✅ 检索轨迹已写入 {note_path}\n   {url}')
PY
fi

rm -f "$out"
