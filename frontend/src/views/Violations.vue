<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const viols = ref<any[]>([])
const unplaced = ref<any[]>([])
const absent = ref<any[]>([])
onMounted(async () => {
  const res = await api('/seating/violations?hall_id=1')
  viols.value = res.violations; unplaced.value = res.unplaced; absent.value = res.absent || []
})
function absentText(a: any) {
  if (a.status === 'reserved') return `占格保留：${a.row + 1} 行 ${a.col + 1} 列，该格别人不得坐`
  if (a.status === 'unseated') return '占格保留策略下未能占格'
  return '释放空出：座位已还给后续考生'
}
</script>
<template>
  <h1>违规</h1>
  <p class="sub">间距不足或同试卷四邻相邻</p>
  <div class="card">
    <table>
      <thead><tr><th>类型</th><th>考生A</th><th>考生B</th><th>说明</th></tr></thead>
      <tbody>
        <tr v-for="(v,i) in viols" :key="i">
          <td>{{ v.kind }}</td><td>{{ v.a_id }}</td><td>{{ v.b_id }}</td><td>{{ v.detail }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!viols.length" class="muted">无违规</p>
  </div>
  <div class="card" v-if="absent.length">
    <h3>缺考名单</h3>
    <div v-for="a in absent" :key="a.id">{{ a.name }}（{{ a.ticket_no }}）· {{ absentText(a) }}</div>
  </div>
  <div class="card" v-if="unplaced.length">
    <h3>未排上</h3>
    <div v-for="u in unplaced" :key="u.id">{{ u.name }}（{{ u.ticket_no }}）</div>
  </div>
  <p class="muted">列表条数与分类数字可分开累计</p>
</template>
