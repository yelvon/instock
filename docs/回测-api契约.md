# 回测 API 契约（二期，与 Vue 前端对接）

详细需求见 [`plan/回测需求.md`](plan/回测需求.md)，前端设计见 [`plan/回测前端设计.md`](plan/回测前端设计.md)。前端技术栈：Vue 3、AG Grid（订单/成交/持仓/账户快照表）、lightweight-charts 或 ECharts（权益/回撤曲线）、TanStack Query（列表缓存与任务轮询）。

## 1. 创建回测任务

`POST /instock/api/backtest/runs`

请求：

```json
{
  "title": "双均线 A 股",
  "dateFrom": "2024-01-01",
  "dateTo": "2024-12-31",
  "universe": { "type": "codes", "codes": ["600000", "000001"] },
  "strategy": {
    "id": "moving_average_cross",
    "params": { "fast": 5, "slow": 20 }
  },
  "broker": {
    "initialCash": 1000000,
    "matchPrice": "next_open",
    "commissionRate": 0.0003,
    "minCommission": 5,
    "stampTaxRate": 0.001,
    "slippageBps": 0
  },
  "risk": {
    "maxPositions": 20,
    "maxWeightPerSymbol": 0.1,
    "maxGrossExposure": 1.0
  },
  "data": {
    "profile": "backtest",
    "priceMode": "raw",
    "requirePrerequisites": true
  }
}
```

响应：

```json
{
  "ok": true,
  "id": "uuid",
  "status": "queued"
}
```

如果数据前置检查失败，返回：

```json
{
  "ok": false,
  "error": "BACKTEST_DATA_GAP",
  "message": "回测主数据缺失",
  "prerequisites": {
    "ok": false,
    "messages": ["交易日历缺 1 天", "cn_stock_spot 缺 2 个交易日"]
  }
}
```

## 2. 任务列表

`GET /instock/api/backtest/runs`

```json
{
  "ok": true,
  "items": [
    {
      "id": "uuid",
      "title": "双均线 A 股",
      "status": "queued|running|success|failed|cancelled",
      "createdAt": "2026-01-15T10:00:00",
      "startedAt": "2026-01-15T10:00:02",
      "finishedAt": "2026-01-15T10:00:12",
      "dateFrom": "2024-01-01",
      "dateTo": "2024-12-31",
      "universe": "codes:2",
      "strategy": "moving_average_cross",
      "progress": {
        "currentDate": "2024-06-03",
        "processedDays": 101,
        "totalDays": 242,
        "message": "撮合 2024-06-03"
      },
      "summary": {
        "totalReturn": 0.123,
        "annualReturn": 0.118,
        "maxDrawdown": -0.082,
        "sharpe": 1.12,
        "tradeCount": 42
      }
    }
  ]
}
```

## 3. 单次回测详情

`GET /instock/api/backtest/runs/{id}`

```json
{
  "ok": true,
  "id": "uuid",
  "status": "success",
  "params": {
    "dateFrom": "2024-01-01",
    "dateTo": "2024-12-31",
    "priceMode": "raw",
    "matchPrice": "next_open"
  },
  "lineage": {
    "profile": "backtest",
    "barProvider": "tushare",
    "barBatchId": "batch-id",
    "mixedSource": false
  },
  "metrics": {
    "totalReturn": 0.123,
    "annualReturn": 0.118,
    "maxDrawdown": -0.082,
    "sharpe": 1.12,
    "volatility": 0.18,
    "winRate": 0.52,
    "turnover": 1.8
  },
  "equity": {
    "time": ["2024-01-02", "2024-01-03"],
    "value": [1.0, 1.01],
    "totalAssets": [1000000, 1010000],
    "dailyReturn": [0, 0.01]
  },
  "benchmark": {
    "name": "沪深300",
    "time": ["2024-01-02", "2024-01-03"],
    "value": [1.0, 1.003]
  },
  "drawdown": {
    "time": ["2024-01-02", "2024-01-03"],
    "value": [0, -0.012],
    "totalAssets": [1000000, 1010000]
  },
  "orders": [
    {
      "orderId": "order-001",
      "createdDate": "2024-01-01",
      "targetDate": "2024-01-02",
      "code": "600000",
      "name": "浦发银行",
      "side": "buy",
      "orderType": "target_weight",
      "requestedQty": 100,
      "targetWeight": 0.1,
      "status": "filled",
      "rejectReason": null,
      "reason": "moving_average_cross"
    },
    {
      "orderId": "order-002",
      "createdDate": "2024-01-02",
      "targetDate": "2024-01-03",
      "code": "000001",
      "name": "平安银行",
      "side": "buy",
      "orderType": "market",
      "requestedQty": 100,
      "targetWeight": null,
      "status": "rejected",
      "rejectReason": "limit_up",
      "reason": "moving_average_cross"
    }
  ],
  "trades": [
    {
      "tradeId": "trade-001",
      "orderId": "order-001",
      "date": "2024-01-02",
      "code": "600000",
      "name": "浦发银行",
      "side": "buy",
      "qty": 100,
      "price": 10.2,
      "amount": 1020,
      "commission": 5,
      "stampTax": 0,
      "transferFee": 0.02,
      "slippageCost": 0,
      "totalCost": 5.02,
      "cashAfter": 998974.98,
      "positionAfter": 100,
      "reason": "moving_average_cross"
    }
  ],
  "positions": [
    {
      "date": "2024-01-02",
      "code": "600000",
      "name": "浦发银行",
      "qty": 100,
      "sellableQty": 0,
      "costPrice": 10.2502,
      "closePrice": 10.3,
      "marketValue": 1030,
      "unrealizedPnl": 4.98,
      "weight": 0.00103,
      "holdingDays": 1
    }
  ],
  "dailyAccounts": [
    {
      "date": "2024-01-02",
      "cash": 998974.98,
      "marketValue": 1030,
      "totalAssets": 1000004.98,
      "dailyReturn": 0.00000498,
      "cumulativeReturn": 0.00000498,
      "drawdown": 0,
      "tradeCount": 1,
      "turnover": 0.00102
    }
  ],
  "error": null
}
```

## 4. 取消任务

`POST /instock/api/backtest/runs/{id}/cancel`

响应：

```json
{ "ok": true, "id": "uuid", "status": "cancelled" }
```

已经完成的任务返回 `ok=false` 和错误码 `BACKTEST_RUN_NOT_CANCELLABLE`。

## 5. 删除任务

`DELETE /instock/api/backtest/runs/{id}`

响应：

```json
{ "ok": true, "id": "uuid", "deletedBytes": 123456 }
```

删除任务时必须同时清理数据库元数据和结果文件。

## 6. 轮询

任务为 `running` 时，前端使用 TanStack Query：`refetchInterval: (q) => (q.state.data?.status === 'running' ? 2000 : false)`。

## 7. 前端页面要求

`features/backtest` 第一版页面包含：

- 参数表单：区间、股票池、策略、资金、成本、撮合口径、数据 profile。
- 任务列表：状态、策略、区间、收益、回撤、创建时间。
- 详情页：权益/回撤图、绩效卡片、订单记录表、成交记录表、持仓表、账户快照表、数据血缘摘要。
- 错误态：展示前置检查失败的缺失日期和建议补跑 job。

## 8. 与一期页面的关系

- 一期已实现：`/instock/api/table_meta`、`/instock/api_data`、`/instock/api/kline_bundle`。
- 回测接口上线后，在 `features/backtest` 增加列表页与详情页即可，无需更换图表库。
