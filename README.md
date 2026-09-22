# ShadeCanopy-01 · 分区气候日志与轮灌计划

温室「分区气候日志与轮灌计划」全栈种子项目（非考勤 OA、非库存）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python Django 5 · Django REST Framework · SimpleJWT · django-cors-headers · Gunicorn |
| 前端 | Vue 3 · Vite · Pinia · Vue Router |
| 数据库 | PostgreSQL 15 |
| 部署 | Docker Compose · Nginx（前端容器反代 `/api` → Django） |

## 路径与端口

- **项目路径**：`D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01\`
- **前端**：http://localhost:3500
- **后端 API**：http://localhost:8500（也可经前端同源 `/api` 访问）
- **PostgreSQL**：localhost:5435

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | admin（管理员，可进 Django Admin） |
| `grower` | `123456` | grower（种植员） |

启动时 `entrypoint.sh` 会执行 `migrate` + `seed_data` 自动写入账号与示例业务数据。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01
docker compose up --build
```

浏览器打开 http://localhost:3500 ，使用 `grower` / `123456` 登录。

停止：

```bash
docker compose down
```

## 业务模块

1. **Auth**：JWT `POST /api/auth/token/`，当前用户 `GET /api/auth/me/`
2. **Greenhouse**：name / location / areaM2 / notes
3. **Zone**：greenhouseId / zoneCode / cropName / status(`idle|growing|fallow`) / isPaused(是否暂停，默认否)；同温室 zoneCode 唯一
4. **ClimateLog**：zoneId / recordedAt / tempC / humidityPct / parUmol / co2Ppm；**humidityPct ∈ [20, 100]**；目标分区已暂停时禁止新建（409）
5. **IrrigationCycle**：zoneId / startAt / durationMin / waterLiters / status(`scheduled|running|done|skipped`)；目标分区已暂停时禁止新建（409）
6. **Dashboard**：温室数、growing 分区数、**暂停分区数 pausedZoneCount**、近 24h 气候日志数、今日 scheduled 轮灌数 → `GET /api/dashboard/`

### 分区暂停规则

- 分区默认 `isPaused=false`。暂停后该区**禁止新建气候记录与轮灌**，已有数据仍可查询；分区列表默认仍返回暂停区，每行带 `isPaused`。
- **切换暂停仅管理员**（role=admin）：`POST /api/zones/{id}/set-paused/`，请求体 `{"isPaused": true|false}`；响应带回 `{id, zoneCode, isPaused}`。种植员调用返回 **403**，普通 `PUT /api/zones/{id}/` 无法修改该字段（只读）。
- 暂停期间向该区新建气候或轮灌一律返回 **409**，响应体示例：
  `{"detail": "分区「A-01」已暂停，禁止新建气候记录，请先恢复该分区", "zoneId": 1, "zoneCode": "A-01", "isPaused": true}`（轮灌提示同理）。
- **单条更新**已有气候/轮灌（仍归属本区）仍允许；但**不得借更新把所属分区改到已暂停区**，否则同样 409。
- 仪表盘 `pausedZoneCount` 与 `isPaused=true` 的分区数一致。
- 前端：分区页可暂停/恢复（仅管理员可见按钮）；新建轮灌的分区下拉默认排除暂停区，可勾选「下拉中显示已暂停分区」开关查看。

## API 一览

| 方法 | 路径 |
| --- | --- |
| POST | `/api/auth/token/` |
| POST | `/api/auth/token/refresh/` |
| GET | `/api/auth/me/` |
| CRUD | `/api/greenhouses/` |
| CRUD | `/api/zones/?greenhouseId=&status=` |
| POST（管理员） | `/api/zones/{id}/set-paused/`（body：`{"isPaused": true\|false}`，种植员 403） |
| CRUD | `/api/climate-logs/?zoneId=`（暂停区新建 409） |
| CRUD | `/api/irrigation-cycles/?zoneId=&status=`（暂停区新建 409） |
| GET | `/api/dashboard/` |

字段对外使用 camelCase（如 `areaM2`、`zoneCode`、`humidityPct`）。

## 本地开发（可选）

**后端**（需本机 Postgres 或已启动 compose 中的 db）：

```bash
cd backend
pip install -r requirements.txt
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5435
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:8500
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

Vite 已将 `/api` 代理到 `http://127.0.0.1:8500`。

## 目录结构

```
ShadeCanopy-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh      # migrate + seed + gunicorn
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/            # settings / urls
│   ├── accounts/          # 自定义 User + role
│   └── core/              # 温室/分区/气候/轮灌 + seed_data
└── frontend/
    ├── Dockerfile
    ├── nginx.conf         # 静态资源 + /api 反代
    ├── package.json
    └── src/               # Vue 页面（叶绿/土色主题）
```

## 配色说明

前端采用叶绿（`#3d6b3a`）与土色（`#8b6b45`）主色，米色底与侧栏深绿渐变，贴近温室场景。
