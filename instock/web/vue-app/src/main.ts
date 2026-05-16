import { createPinia } from "pinia";
import { createApp } from "vue";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "./queryClient";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import "./agGridSetup";
import "./styles/app.css";
import "./styles/ag-grid-instock.css";
import App from "./App.vue";
import router from "./router";

document.documentElement.classList.add("dark");

const app = createApp(App);
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}
app
  .use(createPinia())
  .use(VueQueryPlugin, { queryClient })
  .use(ElementPlus)
  .use(router)
  .mount("#app");
