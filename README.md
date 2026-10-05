# HallSpan 考场间距排座

在考室网格上按最小曼哈顿距离排座，同试卷套不得四邻相邻，并输出违规与统计。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4900 |
| API | http://localhost:9900 |
| API 文档 | http://localhost:9900/docs |
| Postgres | localhost:5450 |

健康检查：`GET http://localhost:9900/api/health`

## 使用说明

1. 在「考室」「考生」「试卷套」确认基础数据。
2. 打开「排座图」执行间距排座。
3. 在「违规」查看间距或同卷相邻问题。
4. 在「统计」查看占用与违规汇总。

## 缺考策略（考室维度，两策略互斥）

- 占格保留（reserve）：每个缺考生在占用账留一行占格，该格别人不得坐，统计占格含此人；未排名单不再把缺考生当可调剂未排。
- 释放空出（release）：缺考生的占用行被删除，格子还给后续考生。
- 策略未配置时按释放空出处理，兼容现网。
- 在「考室」页切换策略即按新策略重排，占用账与排座图同步重写；保存失败时策略字段、占用账、最新方案、统计全部回到保存前。
- 种子数据先按占格保留排座；改为释放空出后，同一缺考生从占用账有行变为无行，排座图与统计一起变。

占用账接口：`GET /api/seating/ledger?hall_id=1`；切换策略：`PUT /api/halls/1/absent-policy`，请求体 `{"policy":"reserve"}` 或 `{"policy":"release"}`。

## 开发与测试

```bash
docker compose exec api pytest -q
```
