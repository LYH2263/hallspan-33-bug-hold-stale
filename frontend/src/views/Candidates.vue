<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
onMounted(async () => { rows.value = await api('/candidates') })
async function toggleAbsent(r: any, ev: Event) {
  const box = ev.target as HTMLInputElement
  const next = box.checked
  const prev = r.absent
  try {
    const res = await api(`/candidates/${r.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ absent: next }),
    })
    r.absent = res.absent
  } catch {
    r.absent = prev
    box.checked = prev
  }
}
</script>
<template>
  <h1>考生名册</h1>
  <p class="sub">夹板名册样式 · 缺考标记在重排时按考室策略落成占用账行</p>
  <div class="hs-clipboard" style="max-width:420px">
    <h2>考生名册 · Clipboard</h2>
    <div v-for="r in rows" :key="r.id ?? JSON.stringify(r)" class="hs-roster-row">
      <div>
        <div>{{ r.name }} <span v-if="r.absent" class="badge badge-warn">缺考</span></div>
        <div class="hs-ticket">{{ r.ticket_no }}</div>
      </div>
      <div>
        卷{{ r.paper_id }} · 室{{ r.hall_id }}
        <label style="margin-left:0.5rem">
          <input type="checkbox" :checked="r.absent" @change="toggleAbsent(r, $event)"> 缺考
        </label>
      </div>
    </div>
  </div>
</template>
