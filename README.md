# TaskFlow

跨平台任務管理系統 — Django 5 REST API + Vue 3 SPA monorepo。

## 專案概述

TaskFlow 是團隊協作型的任務管理工具，提供 Workspace / Project / Task 三層結構，搭配看板拖曳、留言、附件、變更紀錄等核心功能；後續階段將整合 AI 助理進行自然語言任務建立與排程建議。

## Repository 結構

```
TaskFlow/
├── backend/              Django 5 + DRF API（Python 3.13）
│   ├── apps/             業務模組（core / users / workspaces / projects / tasks）
│   ├── config/           Django 設定與主路由
│   ├── tests/            pytest 測試套件
│   └── requirements.txt
├── frontend/             Vue 3 + Vite + TypeScript SPA
│   ├── src/
│   │   ├── api/          Axios client（含 JWT 401 refresh）
│   │   ├── stores/       Pinia stores
│   │   ├── router/       Vue Router + Navigation Guard
│   │   ├── views/        頁面元件
│   │   └── tests/        Vitest 測試
│   └── package.json
└── docker-compose.dev.yml          開發環境 Docker Compose
```

## 技術棧

**後端**：
- Django 5
- Django REST Framework
- PostgreSQL（Supabase）/ SQLite fallback

**前端**：
- Vue 3
- TypeScript
- Vue Router
- PrimeVue（Aura theme）
- TailwindCSS
- vee-validate + Zod

**測試**：
- pytest-django + factory-boy（後端）
- Vitest + @vue/test-utils + @playwright/test（前端）

## 環境準備

### 前置需求

- Python 3.13+
- Node.js 20+ / npm 10+
- （可選）Docker + Docker Compose
- （可選）PostgreSQL — 留空 `DB_HOST` 會自動 fallback 到 SQLite

---

## 後端設定

### 首次啟動

```bash
cd backend
python -m venv venv
source venv/Scripts/activate    # Windows bash
# source venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
cp .env.example .env            # 視需要編輯
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

伺服器運行於 [http://localhost:8000](http://localhost:8000)。

### 健康檢查

```bash
curl http://localhost:8000/api/v1/health/
# {"status":"ok","db":"ok"}
```

### 後端測試指令

```bash
# 所有測試
pytest

# 單一檔案 / 類別 / 方法
pytest tests/test_users/test_models.py
pytest tests/test_users/test_models.py::TestUserSoftDelete
pytest tests/test_users/test_models.py::TestUserSoftDelete::test_soft_delete_sets_deleted_at

# 含覆蓋率報告
pytest --cov=apps --cov-report=term-missing

# 強制重建測試資料庫（schema 異動後執行）
pytest --create-db

# Debug 用：顯示 print 輸出 / 失敗即停
pytest -s -x
```

### Django 管理指令

```bash
python manage.py makemigrations [app_name]   # 產生 migration
python manage.py migrate                     # 套用 migration
python manage.py showmigrations              # 檢視 migration 狀態
python manage.py createsuperuser             # 建立後台管理員
python manage.py shell                       # Django shell（測試 ORM 用）
```

---

## 前端設定

### 首次啟動

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

開發伺服器運行於 [http://localhost:5273](http://localhost:5273)（注意：非 Vite 預設 5173）。

### 前端開發指令

```bash
npm run dev          # Vite 開發伺服器（HMR）
npm run build        # 產生 production build（含 vue-tsc 型別檢查）
npm run preview      # 預覽 production build
npm run type-check   # 僅執行 TypeScript 型別檢查
```

### 前端測試指令

```bash
# Vitest 單元測試（watch 模式）
npm run test

# Vitest 單次執行（CI 用）
npm run test:run

# 覆蓋率報告
npm run coverage

# 特定檔案
npx vitest run src/tests/stores/auth.test.ts
```

---

## Docker Compose（全端整合）

```bash
docker compose -f docker-compose.dev.yml up --build
```

啟動後：
- 後端：[http://localhost:8000](http://localhost:8000)
- 前端：[http://localhost:5273](http://localhost:5273)

### 修改依賴後必須 rebuild

`docker-compose.dev.yml` 只把 source code 用 volume 掛進容器，**Python / npm 套件是裝在 image 裡**。當以下檔案異動時，必須重 build 對應的 service，否則容器內仍是舊套件清單，啟動時可能 `ModuleNotFoundError`：

- `backend/requirements.txt` 改了 → `docker compose -f docker-compose.dev.yml up -d --build backend`
- `frontend/package.json` 改了 → `docker compose -f docker-compose.dev.yml up -d --build frontend`

修完後跑一次健康檢查確認後端正常：

```bash
curl http://localhost:8000/api/v1/health/
# {"status":"ok","db":"ok"}
```

> **症狀提示**：若瀏覽器看到 `net::ERR_EMPTY_RESPONSE`，先看 `docker logs taskflow-backend-1`。Django runserver 的 autoreloader 在啟動時 import 失敗會卡在「等檔案變更」狀態，container 顯示 Up 但 HTTP 沒在服務 — 多半就是 image 沒跟著 requirements 重 build。

---

