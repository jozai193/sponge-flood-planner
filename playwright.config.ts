import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests/browser',timeout:120000,workers:1,use:{baseURL:'http://127.0.0.1:5173',
  ...(process.env.SPONGE_BROWSER==='chrome'?{channel:'chrome'}:{launchOptions:{args:['--enable-webgl','--ignore-gpu-blocklist']}}),viewport:{width:1440,height:960}},
  webServer:{command:'pnpm dev',url:'http://127.0.0.1:5173',reuseExistingServer:true,timeout:60000}});
