# InStock Vue 前端（Vue 3 + Vite + TypeScript）

## 开发

```bash
cd instock/instock/web/vue-app
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 `http://127.0.0.1:5173`）。已代理 **`/instock/api`**、**`/instock/api_data`**、**`/instock/control`** 到本机 Tornado `http://127.0.0.1:9988`，请先启动 Web 服务。

单测：`npm run test`（Vitest）。

## 生产构建

```bash
cd instock/instock/web/vue-app
npm install
npm run build
```

产物输出到与 `vue-app` 同级的 `instock/instock/web/vue-dist/`。重启 Tornado 后访问（根路径 `/` 会 **302** 到 SPA 首页）：

- **首页**：`http://<host>:9988/instock/app/home`
- **数据同步**：`/instock/app/sync`（旧 `/instock/sync` 会 302）
- **数据表**：`/instock/app/table?table_name=…`（旧 `/instock/data?…` 会 302）
- **股票指标**：`/instock/app/indicators?code=…&date=…`（旧 `/instock/data/indicators?…` 会 302）
- **回测（占位）**：`/instock/app/backtest`

未构建时访问 `/instock/app/*` 会返回 503 说明页。

## 技术栈

- Vue 3、Vue Router 4、Pinia、**TanStack Vue Query**
- Element Plus 2 + 暗色 CSS 变量（`html.dark`）
- **AG Grid**（大表）、**lightweight-charts**（K 线+量）、**ECharts**（指标副图）
- **ofetch**、**xlsx**、Vite 6、`manualChunks` 拆包

## 与后端

- 新增 JSON：`/instock/api/table_meta`、`/instock/api/kline_bundle`
- 仍使用：`/instock/api_data`、`/instock/control/attention`、各 `/instock/api/sync/*`

回测二期契约见仓库根 `docs/backtest-api-contract.md`。
