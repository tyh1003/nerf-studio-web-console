# NeRF Studio Web Console

A web-based **NeRF training and 3D point cloud visualization platform** built with **Flask, Nerfstudio, COLMAP, Open3D, LAS/LAZ, and Potree**.

Users can upload multi-view images directly through a browser. The backend automates the reconstruction pipeline, including COLMAP preprocessing, Nerfacto training, point cloud export, Open3D post-processing, LAZ conversion, and Potree Viewer generation.

The reconstructed 3D point cloud can then be explored interactively through the web interface.

---

## Features

The system currently supports:

- Multi-image upload
- Automated COLMAP preprocessing
- Nerfstudio Nerfacto training
- Web-based training control interface
- Configurable training parameters:
  - Maximum training iterations
  - Background color
- Real-time training status updates
- Live training log monitoring
- Automatic PLY point cloud export
- Open3D point cloud processing
- Invalid point filtering
- Spatial region cropping
- Point cloud centering and scaling
- PLY-to-LAZ conversion
- PotreeConverter integration
- Interactive Potree 3D Viewer
- Loading previously completed point cloud projects
- Remote access through ngrok

---

## System Workflow

```text
Multi-view Images
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
       ├── Remove NaN / Inf
       ├── Spatial Filtering
       ├── Centering
       └── Scaling
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

## Project Structure

Recommended GitHub repository structure:

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

The following directories are automatically created at runtime:

```text
projects/
uploads/
```

Each project is stored in a dedicated directory:

```text
projects/
└── project_name_xxxxxxxx/
    ├── input_data/
    ├── outputs/
    ├── export/
    ├── potree/
    └── log.txt
```

These directories contain user-uploaded data, training outputs, and generated reconstruction files. They should not be committed to the public GitHub repository.

---

## System Requirements

Recommended environment:

- Windows 10 / 11
- Python 3.10
- Conda / Miniconda
- NVIDIA GPU
- CUDA
- PyTorch
- Nerfstudio
- COLMAP
- PotreeConverter

Main Python dependencies:

- Flask
- Flask-CORS
- NumPy
- Open3D
- laspy
- lazrs

---

## Installation

### 1. Install Python Dependencies

Install the required Python packages:

```bash
pip install flask flask-cors numpy open3d laspy lazrs
```

Nerfstudio should be installed separately in a dedicated environment according to its official installation instructions.

After installation, verify that the Nerfstudio command-line tools are available:

```bash
ns-train --help
ns-process-data --help
ns-export --help
```

If these commands execute successfully, the Nerfstudio CLI is available in the current environment.

### 2. Configure PotreeConverter

The system uses PotreeConverter to transform processed point clouds into a format suitable for web-based visualization.

Download or compile PotreeConverter and configure the path to its executable.

It is recommended to use an environment variable:

```env
POTREE_CONVERTER=C:\path\to\PotreeConverter.exe
```

Do not commit machine-specific absolute paths or sensitive configuration values to the public repository.

---

## Running the Application

First, activate the Nerfstudio Conda environment:

```bash
conda activate nerfstudio
```

Navigate to the project directory:

```bash
cd path\to\nerf_web_project
```

Start the Flask application:

```bash
python app.py
```

By default, the web interface is available at:

```text
http://127.0.0.1:5000
```

---

## Usage

### 1. Create a New Training Task

Open the web interface and follow these steps:

1. Enter a project name.
2. Select multiple images captured from different viewpoints.
3. Enable advanced mode if additional configuration is needed.
4. Click **Start Training**.

The backend executes the following pipeline:

```text
COLMAP
   ↓
Nerfacto Training
   ↓
Point Cloud Export
   ↓
Open3D Processing
   ↓
LAZ Conversion
   ↓
PotreeConverter
```

### 2. Advanced Mode

Advanced mode allows users to configure selected training parameters.

#### Maximum Training Iterations

Example:

```text
5000
```

This corresponds to the Nerfacto parameter:

```text
--max-num-iterations
```

#### Background Color

Supported options:

```text
white
black
random
```

---

## Point Cloud Processing

After Nerfstudio training is complete, the system exports a point cloud using:

```bash
ns-export pointcloud
```

The generated file is:

```text
point_cloud.ply
```

Open3D is then used to process the exported point cloud before visualization.

### Invalid Point Filtering

Points containing invalid 3D coordinates are removed, including:

```text
NaN
Inf
```

### Spatial Cropping

The system applies spatial filtering to remove points outside a predefined 3D region.

For example:

```text
x ∈ [-1, 1]
y ∈ [-1, 1]
z ∈ [-1, 1]
```

This helps remove noisy points located far from the primary reconstructed object.

### Point Cloud Centering

The mean position of the point cloud is calculated:

```text
center = mean(points)
```

The point cloud is then repositioned relative to its center for more convenient processing and visualization.

### Point Cloud Scaling

The system normalizes the point cloud based on its maximum distance from the center, bringing its coordinates into a more manageable range.

---

## LAZ Conversion

After processing, the point cloud is converted into:

```text
point_cloud.laz
```

The converted point cloud retains information such as:

- X coordinates
- Y coordinates
- Z coordinates
- RGB colors

The LAZ file is subsequently passed to PotreeConverter.

---

## Potree Visualization

The processed LAZ file is converted using:

```text
PotreeConverter
```

PotreeConverter generates the data required for the web-based point cloud viewer.

Once conversion is complete, users can explore the reconstruction through the integrated **Potree 3D Viewer**.

---

## Loading Previously Completed Projects

The application supports reopening previously completed reconstruction projects.

From the **Load Completed Point Cloud** section, select an existing project.

If the project contains:

```text
point_cloud.laz
```

along with the generated Potree Viewer data, the 3D reconstruction can be loaded directly without repeating the training process.

---

## Remote Access with ngrok

The application supports remote access through ngrok while keeping Flask and NeRF training on the local machine.

This allows external users to access the web interface while GPU-intensive computation continues to run on the host computer.

### 1. Start the Flask Server

```bash
python app.py
```

### 2. Start ngrok

Open another terminal and run:

```bash
ngrok http 5000
```

ngrok generates a public URL similar to:

```text
https://xxxxxxxx.ngrok-free.app
```

External users can then use the public URL to:

- Upload images
- Create training tasks
- Monitor training progress
- View training logs
- Explore reconstructed point clouds through Potree

All GPU computations remain on the local host machine.

### Remote Access Preview

<img width="922" height="758" alt="NeRF Studio Web Console remote access interface" src="https://github.com/user-attachments/assets/c45ce96a-4124-47cd-847a-2a3ba706e3c1" />

---

## ngrok Architecture

```text
Remote User
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

Remote access remains available as long as:

- The host computer is powered on.
- The Flask application is running.
- The ngrok tunnel is active.
- The host maintains an internet connection.

**Security note:** Exposing the application through ngrok makes the interface accessible from outside the local network. Use appropriate access restrictions before allowing untrusted users to upload files or trigger GPU-intensive training tasks.

---

## Technologies Used

| Category | Technologies |
|---|---|
| Web Backend | Python, Flask, Flask-CORS |
| 3D Reconstruction | Nerfstudio, Nerfacto, COLMAP |
| Point Cloud Processing | Open3D, NumPy |
| Point Cloud Formats | PLY, LAS/LAZ |
| Point Cloud Conversion | laspy, lazrs, PotreeConverter |
| 3D Visualization | Potree |
| GPU Computing | PyTorch, CUDA, NVIDIA GPU |
| Remote Access | ngrok |

---

## Project Overview

This project focuses on integrating existing 3D reconstruction and point cloud processing tools into a unified, browser-accessible workflow.

Rather than implementing NeRF training algorithms from scratch, the system automates the end-to-end process from multi-view image upload to interactive 3D visualization, reducing the need for users to manually execute multiple command-line tools.
