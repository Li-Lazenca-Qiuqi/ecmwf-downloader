import { type ReactNode } from 'react'

function tokens(line: string): ReactNode[] {
  const result: ReactNode[] = []
  let cursor = 0
  for (const match of line.matchAll(/"(?:\\.|[^"\\])*"|\b(?:true|false|null|-?\d+(?:\.\d+)?)\b/g)) {
    const start = match.index!
    if (start > cursor) result.push(line.slice(cursor, start))
    const token = match[0]
    const key = line.slice(start + token.length).trimStart().startsWith(':')
    result.push(<span key={start} className={key ? 'code-key' : token.startsWith('"') ? 'code-string' : 'code-literal'}>{token}</span>)
    cursor = start + token.length
  }
  if (cursor < line.length) result.push(line.slice(cursor))
  return result
}

export default function RequestPreviewCode({ payload }: { payload: Record<string, unknown> }) {
  const text = JSON.stringify(payload, null, 2).replace(/\[\n(?:\s+(?:"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?),?\n)+\s*\]/g, (block) => {
    const values: unknown[] = JSON.parse(block)
    const inline = '[' + values.map((value) => JSON.stringify(value)).join(', ') + ']'
    return inline.length <= 32 ? inline : block
  })
  return <pre className="request-code" aria-label="请求参数预览"><code>{text.split('\n').map((line, index) => <span className="code-line" key={index}>{tokens(line)}</span>)}</code></pre>
}
