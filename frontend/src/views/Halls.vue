<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const POLICIES = [
  { value: 'reserve', label: '占格保留' },
  { value: 'release', label: '释放空出' },
]
onMounted(async () => { rows.value = await api('/halls') })
async function changePolicy(r: any, ev: Event) {
  const sel = ev.target as HTMLSelectElement
  const next = sel.value
  const prev = r.absent_policy
  r.saving = true
  r.notice = ''
  r.error = ''
  try {
    const res = await api(`/halls/${r.id}/absent-policy`, {
      method: 'PUT',
      body: JSON.stringify({ policy: next }),
    })
    r.absent_policy = res.absent_policy
    r.notice = '已保存并按新策略重排'
  } catch {
    // 保存失败：后端已整体回滚，前端选择一并回退
    r.absent_policy = prev
    sel.value = prev
    r.error = '保存失败，已保持原策略'
  } finally {
    r.saving = false
  }
}
</script>
<template>
  <h1>考室</h1>
  <p class="sub">考室网格与最小曼哈顿间距 · 缺考策略二选一（互斥），未配置按释放空出</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>行</th><th>列</th><th>最小间距</th><th>缺考策略</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.rows }}</td><td>{{ r.cols }}</td><td>{{ r.min_manhattan }}</td>
          <td>
            <select :value="r.absent_policy" :disabled="r.saving" @change="changePolicy(r, $event)">
              <option v-for="p in POLICIES" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
            <span v-if="!r.absent_policy_configured" class="muted">（未配置，按释放）</span>
            <div v-if="r.notice" class="badge badge-ok">{{ r.notice }}</div>
            <div v-if="r.error" class="badge badge-bad">{{ r.error }}</div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
