import type {QueryResponse} from '../types'
export async function ask(question:string):Promise<QueryResponse>{
  const response=await fetch('/api/v1/query',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer demo-token'},body:JSON.stringify({question})})
  if(!response.ok){const body=await response.json();throw new Error(typeof body.detail==='string'?body.detail:'请求失败')}
  return response.json()
}

