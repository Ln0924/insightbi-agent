export interface Evidence {evidence_id:string;step_id:string;sql:string;columns:string[];rows:Record<string,unknown>[];row_count:number;summary:string}
export interface ChartSpec {type:'line'|'bar'|'pie'|'table'|'kpi';title:string;x_field?:string;y_fields:string[];data:Record<string,unknown>[]}
export interface QueryResponse {trace_id:string;status:string;mode:string;answer:string;sql:string[];evidence:Evidence[];charts:ChartSpec[];warnings:string[];latency_ms:number}

