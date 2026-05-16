# 回测 API 契约（二期，与 Vue 前端对接）

前端技术栈：Vue 3、AG Grid（成交/持仓/日收益表）、lightweight-charts 或 ECharts（权益/回撤曲线）、TanStack Query（列表缓存与任务轮询）。

## 1. 任务列表（示例）

`GET /instock/api/backtest/runs`（路径待定）

```json
{
  "ok": true,
  "items": [
    {
      "id": "uuid",
      "title": "双均线 A 股",
      "status": "queued|running|success|failed",
      "createdAt": "2026-01-15T10:00:00",
      "universe": "沪深主板"
    }
  ]
}
```

## 2. 单次回测详情（示例）

`GET /instock/api/backtest/runs/:id`

```json
{
  "ok": true,
  "id": "uuid",
  "status": "success",
  "equity": { "time": ["2024-01-02", "2024-01-03"], "value": [1.0, 1.01] },
  "benchmark": { "time": [], "value": [] },
  "drawdown": { "time": [], "value": [] },
  "trades": [{ "date": "2024-01-02", "code": "600000", "side": "buy", "qty": 100, "price": 10.2 }],
  "positions": []
}
```

## 3. 轮询

任务为 `running` 时，前端使用 TanStack Query：`refetchInterval: (q) => (q.state.data?.status === 'running' ? 2000 : false)`。

## 4. 与一期页面的关系

- 一期已实现：`/instock/api/table_meta`、`/instock/api_data`、`/instock/api/kline_bundle`。
- 回测接口上线后，在 `features/backtest` 增加列表页与详情页即可，无需更换图表库。
