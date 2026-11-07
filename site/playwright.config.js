import {defineConfig} from '@playwright/test';
import {previewUrl} from './scripts/preview.mjs';
const baseURL=previewUrl();
export default defineConfig({
 testDir:'./e2e',testMatch:'**/*.spec.js',fullyParallel:true,workers:2,
 timeout:30000,retries:0,reporter:'list',
 use:{baseURL,headless:true,channel:'chromium',screenshot:'only-on-failure',trace:'off',video:'off'},
 webServer:{command:'node scripts/preview.mjs',url:baseURL,reuseExistingServer:false,timeout:10000},
});
