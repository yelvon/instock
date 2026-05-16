import { ofetch } from "ofetch";

/** 同域请求（开发环境由 Vite 代理 /instock） */
export const $api = ofetch.create({
  credentials: "same-origin",
  retry: 0,
});
