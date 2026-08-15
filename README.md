# NeRF Studio Web Console

一套以 **Flask、Nerfstudio、COLMAP、Open3D、LAS/LAZ 與 Potree** 建立的 Web NeRF 訓練與三維點雲展示系統。

使用者可以直接透過瀏覽器上傳多視角影像，由後端自動完成 COLMAP 前處理、Nerfacto 訓練、點雲匯出、Open3D 點雲處理、LAZ 轉換以及 Potree Viewer 建立，最後直接在網頁中瀏覽三維重建結果。

---

## 功能

目前系統包含：

* 多張影像上傳
* COLMAP 自動前處理
* Nerfstudio Nerfacto 訓練
* Web 訓練控制介面
* 訓練參數設定

  * 最大迭代次數
  * Background Color
* 訓練狀態即時顯示
* 訓練 Log 即時更新
* 自動匯出 PLY 點雲
* Open3D 點雲處理
* 無效點過濾
* 空間區域裁切
* 點雲中心化與縮放
* PLY → LAZ
* PotreeConverter 整合
* Potree 3D Viewer
* 載入已完成的點雲專案
* ngrok 遠端存取

---

# 系統流程

```text
多視角影像
    │
    ▼
Flask Web Upload
    │
    ▼
COLMAP
    │
    ▼
Nerfstudio / Nerfacto
    │
    ▼
PLY Point Cloud
    │
    ▼
Open3D
    │
    ├── 移除 NaN / Inf
    ├── 空間範圍過濾
    ├── 中心化
    └── 縮放
    │
    ▼
LAZ
    │
    ▼
PotreeConverter
    │
    ▼
Potree 3D Viewer
```

---

# 專案結構

GitHub Repository 建議結構：

```text
nerf_web_project/
│
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
└── templates/
    └── index.html
```

程式執行後會自動建立：

```text
projects/
uploads/
```

其中 `projects/` 會包含：

```text
projects/
└── project_name_xxxxxxxx/
    ├── input_data/
    ├── outputs/
    ├── export/
    ├── potree/
    └── log.txt
```

這些資料屬於執行期間產生的使用者資料與模型輸出，不應提交至 GitHub。

---

# 系統需求

建議環境：

* Windows 10 / 11
* Python 3.10
* Conda / Miniconda
* NVIDIA GPU
* CUDA
* PyTorch
* Nerfstudio
* COLMAP
* PotreeConverter

Python 主要套件：

* Flask
* Flask-CORS
* NumPy
* Open3D
* laspy
* lazrs

---

# Python 套件安裝

安裝基本 Python Dependencies：

```bash
pip install flask flask-cors numpy open3d laspy lazrs
```

Nerfstudio 建議依照官方安裝方式另外建立環境。

安裝完成後可確認：

```bash
ns-train --help
ns-process-data --help
ns-export --help
```

若以上指令可以正常執行，即表示 Nerfstudio CLI 已成功加入目前環境。

---

# PotreeConverter 設定

本系統使用 PotreeConverter 將處理後的點雲轉換為 Web Viewer 所需資料。

請自行下載或編譯 PotreeConverter，並設定其執行檔位置。

建議使用環境變數：

```env
POTREE_CONVERTER=C:\path\to\PotreeConverter.exe
```

請勿直接將個人電腦上的絕對路徑提交至公開 Repository。

---

# 啟動系統

首先啟動 Nerfstudio Conda Environment：

```bash
conda activate nerfstudio
```

進入專案：

```bash
cd path\to\nerf_web_project
```

執行：

```bash
python app.py
```

預設網址：

```text
http://127.0.0.1:5000
```

---

# 使用方法

## 1. 建立新任務

開啟 Web Interface 後：

1. 輸入專案名稱
2. 選擇多張不同視角照片
3. 視需要開啟進階模式
4. 按下「開始訓練」

後端會依序執行：

```text
COLMAP
→ Nerfacto
→ Point Cloud Export
→ Open3D Processing
→ LAZ
→ PotreeConverter
```

---

# 進階模式

啟用：

```text
啟用高級模式
```

目前可設定：

## 最大迭代次數

例如：

```text
5000
```

對應 Nerfacto：

```text
--max-num-iterations
```

## 背景顏色

支援：

```text
white
black
random
```

---

# 點雲處理

Nerfstudio 訓練完成後，系統會使用：

```bash
ns-export pointcloud
```

產生：

```text
point_cloud.ply
```

接著由 Open3D 進行後處理。

---

## 無效點清除

會移除包含：

```text
NaN
Inf
```

的三維座標。

---

## 空間裁切

目前會對點雲進行三維空間過濾，例如：

```text
x ∈ [-1, 1]
y ∈ [-1, 1]
z ∈ [-1, 1]
```

藉此移除距離主要重建物體過遠的雜訊點。

---

## 中心化

使用點雲平均位置：

```text
center = mean(points)
```

重新將點雲置於較適合處理與展示的位置。

---

## 縮放

系統會依點雲最大距離進行 normalization，使點雲座標落在較合理的範圍。

---

# LAZ

處理後的點雲會轉換成：

```text
point_cloud.laz
```

其中保留：

* X
* Y
* Z
* RGB

等資訊。

---

# Potree

LAZ 完成後會送入：

```text
PotreeConverter
```

產生 Web-based Point Cloud Viewer。

完成後可以直接在網站中的：

```text
3D 點雲瀏覽器 (Potree)
```

進行操作。

---

# 載入已完成點雲

系統支援重新載入之前完成的專案。

在：

```text
載入訓練完成的點雲
```

選擇專案後，如果該專案已有：

```text
point_cloud.laz
```

與 Potree Viewer 資料，即可直接重新開啟三維成果，而不需要重新訓練。

---

# 使用 ngrok 開放外部使用

本系統可以讓 Flask 與 NeRF Training 保持在本機 GPU 執行，並透過 ngrok 對外提供 Web Interface。

首先啟動：

```bash
python app.py
```

另外開啟一個 Terminal：

```bash
ngrok http 5000
```

ngrok 會產生類似：

```text
https://xxxxxxxx.ngrok-free.app
```

的公開網址。

其他使用者即可透過該網址：

* 上傳圖片
* 建立訓練任務
* 查看訓練狀態
* 查看 Log
* 瀏覽最終 Potree 點雲

實際 GPU 運算仍在主機端執行。

<img width="922" height="758" alt="image" src="https://github.com/user-attachments/assets/c45ce96a-4124-47cd-847a-2a3ba706e3c1" />

---

# ngrok 架構

```text
外部使用者
     │
     ▼
ngrok Endpoint
     │
     ▼
Flask Server
     │
     ▼
Nerfstudio
     │
     ▼
Local NVIDIA GPU
```

因此只要：

* 主機保持開機
* Flask 正在執行
* ngrok 正在執行
* 網路保持連線

外部使用者就能持續使用系統。


