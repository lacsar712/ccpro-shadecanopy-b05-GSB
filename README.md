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
3. **Zone**：greenhouseId / zoneCode / cropName / status(`idle|growing|fallow`) / isPaused；同温室 zoneCode 唯一
4. **ClimateLog**：zoneId / recordedAt / tempC / humidityPct / parUmol / co2Ppm；**humidityPct ∈ [20, 100]**
5. **IrrigationCycle**：zoneId / startAt / durationMin / waterLiters / status(`scheduled|running|done|skipped`)
6. **Dashboard**：温室数、growing 分区数、暂停分区数、近 24h 气候日志数、今日 scheduled 轮灌数 → `GET /api/dashboard/`

### 分区暂停规则

- 分区新增只读字段 `isPaused`（是否暂停，默认 `false`）；分区列表默认仍返回暂停区，每行都带 `isPaused`。
- **仅管理员（role=admin）**可切换暂停：
  - `POST /api/zones/{id}/pause/`：暂停分区
  - `POST /api/zones/{id}/resume/`：恢复分区
  - 种植员（role=grower）调用返回 **403**；两个接口响应体均为 `{ "id", "zoneCode", "isPaused" }`。
  - `isPaused` 不接受经普通新建 / 编辑接口写入（序列化器中为只读），只能经上述两个管理员接口切换。
- 分区暂停后：
  - **新建**气候记录或轮灌到该分区一律返回 **409**，`detail` 为中文并明确包含「暂停 / 禁止新建」。
  - 该分区**已有**气候、轮灌数据仍可查询，也可**单条更新**（改温湿度、时间、状态等）。
  - 但不得借更新把气候或轮灌的所属分区改到已暂停区，违反时同样返回 **409**。
- 仪表盘 `pausedZoneCount` 与 `isPaused = true` 的分区数严格一致。
- 前端：分区页每行有「已暂停 / 正常」标记，管理员可见「暂停 / 恢复」按钮；新建轮灌的分区下拉默认排除暂停区，勾选「显示暂停分区」后可展开（编辑中原属暂停区的轮灌记录时，该分区在下拉中仍可见）。

## API 一览

| 方法 | 路径 |
| --- | --- |
| POST | `/api/auth/token/` |
| POST | `/api/auth/token/refresh/` |
| GET | `/api/auth/me/` |
| CRUD | `/api/greenhouses/` |
| CRUD | `/api/zones/?greenhouseId=&status=` |
| POST | `/api/zones/{id}/pause/`（仅管理员，种植员 403） |
| POST | `/api/zones/{id}/resume/`（仅管理员，种植员 403） |
| CRUD | `/api/climate-logs/?zoneId=`（目标分区暂停时新建返回 409） |
| CRUD | `/api/irrigation-cycles/?zoneId=&status=`（目标分区暂停时新建返回 409） |
| GET | `/api/dashboard/`（含 `pausedZoneCount`） |

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
