import type {Evidence} from '../types'
export function EvidencePanel({items}:{items:Evidence[]}){return <section className="panel"><h3>证据与 SQL</h3>{items.map(item=><details key={item.evidence_id}><summary>{item.step_id} · {item.row_count} 行 · {item.evidence_id}</summary><pre>{item.sql}</pre><div className="table-wrap"><table><thead><tr>{item.columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{item.rows.slice(0,20).map((row,i)=><tr key={i}>{item.columns.map(c=><td key={c}>{String(row[c]??'')}</td>)}</tr>)}</tbody></table></div></details>)}</section>}

