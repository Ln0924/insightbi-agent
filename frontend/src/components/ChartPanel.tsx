import {useEffect,useRef} from 'react'
import {init,use} from 'echarts/core'
import {BarChart,LineChart} from 'echarts/charts'
import {GridComponent,LegendComponent,TooltipComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'
import type {ChartSpec} from '../types'
use([BarChart,LineChart,GridComponent,LegendComponent,TooltipComponent,CanvasRenderer])
export function ChartPanel({chart}:{chart:ChartSpec}){
  const container=useRef<HTMLDivElement>(null)
  const x=chart.x_field||'';const option={tooltip:{trigger:'axis'},legend:{},grid:{left:48,right:24,bottom:40,top:50},xAxis:{type:'category',data:chart.data.map(r=>String(r[x]??''))},yAxis:{type:'value'},series:chart.y_fields.map(field=>({name:field,type:chart.type==='bar'?'bar':'line',smooth:true,data:chart.data.map(r=>Number(r[field]??0))}))}
  useEffect(()=>{if(!container.current)return;const instance=init(container.current);instance.setOption(option);const resize=()=>instance.resize();window.addEventListener('resize',resize);return()=>{window.removeEventListener('resize',resize);instance.dispose()}},[chart])
  return <section className="panel"><h3>{chart.title}</h3><div ref={container} style={{height:300}}/></section>
}
