import os
import subprocess
import threading
import uuid
import re
import open3d as o3d
import numpy as np
import shutil
import laspy
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
# CORS(app)

UPLOAD_FOLDER = 'uploads'
PROJECTS_FOLDER = 'projects'
POTREE_CONVERTER = os.getenv(
    "POTREE_CONVERTER",
    r"C:\path\to\PotreeConverter.exe"
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROJECTS_FOLDER, exist_ok=True)

jobs = {}

# -------------------------------------------------------
# 🧠 NeRF 訓練流程
# -------------------------------------------------------
def run_nerf_pipeline(job_id, project_path):
    my_env = os.environ.copy()
    my_env["PYTHONUTF8"] = "1"

    input_data_path = os.path.join(project_path, 'input_data')
    log_file_path = os.path.join(project_path, 'log.txt')

    try:
        # 1️⃣ COLMAP 前處理
        jobs[job_id]['status'] = '正在執行 COLMAP 前處理...'
        colmap_cmd = [
            'ns-process-data', 'images',
            '--data', input_data_path,
            '--output-dir', project_path,
            '--sfm-tool', 'colmap',
            '--feature-type', 'sift',
            '--matcher-type', 'NN',
            '--matching-method', 'exhaustive',
            '--verbose'
        ]
        run_and_log(colmap_cmd, log_file_path, my_env, job_id)

        # 2️⃣ NeRF 訓練
        max_iter = jobs[job_id].get('max_iter', '5000')
        bg_color = jobs[job_id].get('background_color', 'white')
        jobs[job_id]['status'] = f'正在訓練 NeRF 模型 (迭代 {max_iter})...'
        nerf_cmd = [
            'ns-train', 'nerfacto',
            '--data', project_path,
            '--output-dir', os.path.join(project_path, 'outputs'),
            '--project-name', jobs[job_id]['project_name'],
            '--viewer.quit-on-train-completion', 'True',
            '--max-num-iterations', max_iter,
            '--pipeline.model.background-color', bg_color
        ]
        run_and_log(nerf_cmd, log_file_path, my_env, job_id)

        # 3️⃣ 匯出點雲
        jobs[job_id]['status'] = '正在尋找訓練結果並匯出點雲...'
        outputs_path = os.path.join(project_path, "outputs")
        if not os.path.exists(outputs_path):
            raise FileNotFoundError(f"⚠️ 找不到主輸出資料夾: {outputs_path}")

        project_outputs_dirs = [
            d for d in os.listdir(outputs_path)
            if os.path.isdir(os.path.join(outputs_path, d))
        ]
        if not project_outputs_dirs:
            raise FileNotFoundError(f"⚠️ 在 {outputs_path} 中找不到任何專案輸出")

        latest_project_output = max(
            project_outputs_dirs,
            key=lambda d: os.path.getmtime(os.path.join(outputs_path, d))
        )
        nerfacto_path = os.path.join(outputs_path, latest_project_output, "nerfacto")
        if not os.path.exists(nerfacto_path):
            raise FileNotFoundError(f"⚠️ 找不到 Nerfacto 輸出資料夾: {nerfacto_path}")

        timestamp_dirs = [
            d for d in os.listdir(nerfacto_path)
            if os.path.isdir(os.path.join(nerfacto_path, d))
        ]
        if not timestamp_dirs:
            raise FileNotFoundError(f"⚠️ 在 {nerfacto_path} 中找不到任何時間戳訓練結果")

        latest_timestamp_dir = max(timestamp_dirs)
        config_path = os.path.join(nerfacto_path, latest_timestamp_dir, "config.yml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"⚠️ 最終找不到設定檔: {config_path}")

        export_dir = os.path.join(project_path, "export")
        os.makedirs(export_dir, exist_ok=True)

        export_cmd = [
            "ns-export", "pointcloud",
            "--load-config", config_path,
            "--output-dir", export_dir,
            "--num-points", "2000000",
            "--normal-method", "open3d"
        ]
        run_and_log(export_cmd, log_file_path, my_env, job_id)

        ply_path = os.path.join(export_dir, "point_cloud.ply")
        if not os.path.exists(ply_path):
            raise FileNotFoundError("⚠️ 匯出點雲後找不到 point_cloud.ply 檔案")

        # 4️⃣ 縮放、中心化、過濾、轉 LAZ
        jobs[job_id]['status'] = '正在縮放、中心化、過濾並轉換為 LAZ 格式...'
        laz_path = os.path.join(export_dir, "point_cloud.laz")
        convert_ply_to_laz(ply_path, laz_path)

        # 5️⃣ Potree 轉換
        jobs[job_id]['status'] = '正在轉換 Potree 視覺化頁面...'
        potree_dir = os.path.join(project_path, "potree")
        os.makedirs(potree_dir, exist_ok=True)

        potree_converter_abs = os.path.abspath(POTREE_CONVERTER)
        laz_path_abs = os.path.abspath(laz_path)
        potree_dir_abs = os.path.abspath(potree_dir)
        potree_converter_cwd = os.path.dirname(potree_converter_abs)

        if not os.path.exists(potree_converter_abs):
            raise FileNotFoundError(
                f"FATAL: PotreeConverter.exe 不存在於指定路徑: {potree_converter_abs}"
            )

        potree_cmd = [
            potree_converter_abs, laz_path_abs,
            "-o", potree_dir_abs,
            "--generate-page", "index",
            "--title", jobs[job_id]['project_name'],
            "--material", "RGB"
        ]
        run_and_log(potree_cmd, log_file_path, my_env, job_id, cwd=potree_converter_cwd)

        jobs[job_id]['potree_url'] = f"/potree/{os.path.basename(project_path)}/index.html"
        jobs[job_id]['status'] = "✅ 完成：Potree 檢視可用！"

    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        error_message = f"❌ 錯誤：{e}"
        print(error_message)
        if job_id in jobs:
            jobs[job_id]['status'] = error_message
        with open(log_file_path, 'a', encoding='utf-8') as log:
            log.write(f"\n\n!!! PIPELINE FAILED !!!\n{error_message}\n")

    finally:
        if job_id in jobs:
            jobs[job_id]['progress'] = 100


# -------------------------------------------------------
# 🧩 工具函式
# -------------------------------------------------------
def run_and_log(command, log_path, env, job_id, cwd=None):
    command_str = ' '.join(f'"{c}"' if ' ' in c else c for c in command)
    log_entry = (
        f"\n--- [INFO] Running Command ---\n"
        f"Job ID: {job_id}\n"
        f"Work Dir: {cwd or os.getcwd()}\n"
        f"Command: {command_str}\n"
        f"-----------------------------\n\n"
    )
    print(log_entry)
    with open(log_path, 'a', encoding='utf-8') as log:
        log.write(log_entry)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env,
        cwd=cwd,
        bufsize=1,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    with open(log_path, 'a', encoding='utf-8') as log:
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
            log.write(line)
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command_str)


def convert_ply_to_laz(input_ply, output_laz):
    """讀取 PLY，縮放、中心化、過濾 [-1,1]^3 並轉 LAZ 格式"""
    pcd = o3d.io.read_point_cloud(input_ply)
    points = np.asarray(pcd.points)
    print(f"🔍 讀取 PLY 點雲：{len(points)} 點")

    if len(points) == 0:
        raise ValueError("讀取的 PLY 點雲為空，無法繼續轉換。")

    mask = np.isfinite(points).all(axis=1)
    points = points[mask]

    # 🎯 空間範圍過濾 [-1,1]^3
    inside_box = np.all((points >= -1) & (points <= 1), axis=1)
    points = points[inside_box]
    print(f"✅ 範圍過濾後剩餘點數：{len(points)}")

    if len(points) == 0:
        raise ValueError("⚠️ 範圍過濾後沒有點雲資料。")

    center = np.mean(points, axis=0)
    points_centered = points - center
    max_dist = np.max(np.linalg.norm(points_centered, axis=1))
    points_scaled = points_centered / max_dist if max_dist > 1e-6 else points_centered

    header = laspy.LasHeader(point_format=3, version="1.4")
    header.x_scale = header.y_scale = header.z_scale = 0.000001
    header.x_offset, header.y_offset, header.z_offset = -center

    laz = laspy.LasData(header)
    laz.x, laz.y, laz.z = points_scaled[:, 0], points_scaled[:, 1], points_scaled[:, 2]

    if pcd.has_colors():
        colors = np.asarray(pcd.colors)[mask][inside_box]
        laz.red = (colors[:, 0] * 65535).astype(np.uint16)
        laz.green = (colors[:, 1] * 65535).astype(np.uint16)
        laz.blue = (colors[:, 2] * 65535).astype(np.uint16)

    laz.write(output_laz)
    print(f"✅ 已成功轉換並儲存為 LAZ 格式：{output_laz}")


# -------------------------------------------------------
# 🏠 Flask 路由
# -------------------------------------------------------
@app.route('/')
def index():
    project_list = []
    if os.path.exists(PROJECTS_FOLDER):
        for name in sorted(os.listdir(PROJECTS_FOLDER)):
            path = os.path.join(PROJECTS_FOLDER, name)
            if os.path.isdir(path):
                project_list.append({"name": name})
    return render_template('index.html', running_jobs=jobs, existing_projects=project_list)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'images' not in request.files or not request.files.getlist('images')[0].filename:
        return "沒有選擇圖片檔案", 400

    files = request.files.getlist('images')
    project_name_raw = request.form.get('project_name', 'nerf-project').strip()
    project_name = re.sub(r'[\\/*?:"<>|]', "", project_name_raw) or "nerf-project"

    enable_advanced = request.form.get('enable_advanced', 'off') == 'on'
    max_iter = request.form.get('max_iter', '5000') if enable_advanced else '5000'
    bg_color = request.form.get('background_color', 'white') if enable_advanced else 'white'

    job_id = str(uuid.uuid4())
    folder_name = f"{project_name}_{job_id[:8]}"
    project_path = os.path.join(PROJECTS_FOLDER, folder_name)
    os.makedirs(os.path.join(project_path, 'input_data'), exist_ok=True)

    for f in files:
        if f.filename:
            f.save(os.path.join(project_path, 'input_data', f.filename))

    jobs[job_id] = {
        "project_name": project_name,
        "status": "任務已建立，排隊等待執行...",
        "project_path": project_path,
        "progress": 0,
        "max_iter": max_iter,
        "background_color": bg_color,
        "potree_url": None
    }

    threading.Thread(target=run_nerf_pipeline, args=(job_id, project_path), daemon=True).start()
    return redirect(url_for('progress', job_id=job_id))


@app.route('/load_project', methods=['POST'])

def load_project():
    """載入已訓練完成的點雲專案"""
    selected = request.form.get('selected_project')
    if not selected:
        return redirect('/')

    project_path = os.path.join(PROJECTS_FOLDER, selected)
    export_path = os.path.join(project_path, "export")
    laz_file = os.path.join(export_path, "point_cloud.laz")
    potree_path_abs = os.path.join(project_path, "potree", "index.html")

    job_id = str(uuid.uuid4())
    status_message = ""
    potree_url = None

    # ✅ 確認點雲是否存在
    if os.path.exists(laz_file):
        status_message = "✅ 已載入訓練完成的點雲"
        # 若已存在 Potree 視覺化頁面則直接提供連結
        if os.path.exists(potree_path_abs):
            potree_url = f"/potree/{selected}/index.html"
    else:
        status_message = "⚠️ 尚未匯出點雲或訓練未完成"

    jobs[job_id] = {
        "project_name": selected.split('_')[0],
        "project_path": project_path,
        "status": status_message,
        "progress": 100,
        "potree_url": potree_url
    }

    return redirect(url_for('progress', job_id=job_id))



@app.route('/progress/<job_id>')
def progress(job_id):
    project_list = []
    if os.path.exists(PROJECTS_FOLDER):
        for name in sorted(os.listdir(PROJECTS_FOLDER)):
            path = os.path.join(PROJECTS_FOLDER, name)
            if os.path.isdir(path):
                project_list.append({"name": name})
    return render_template('index.html', job_id=job_id, running_jobs=jobs, existing_projects=project_list)


@app.route('/status/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "找不到任務"}), 404

    log_content = ""
    log_file = os.path.join(job.get("project_path", ""), "log.txt")
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()[-8000:]
        except Exception as e:
            log_content = f"無法讀取日誌: {e}"

    return jsonify({
        "status": job.get("status", "未知"),
        "progress": job.get("progress", 0),
        "potree_url": job.get("potree_url"),
        "log_content": log_content
    })


@app.route('/potree/<project>/<path:filename>')
def serve_potree(project, filename):
    directory = os.path.join(PROJECTS_FOLDER, project, "potree")
    return send_from_directory(directory, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
