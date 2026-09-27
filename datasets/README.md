# 下载项目视频

本数据集包含项目使用的 **12 个 MP4 视频**，总计 **586,000,478 字节（约 559 MiB）**。
下载后恢复到 `CrossSight/dataset/`，可直接供现有流水线读取。

## 一键下载

需要 **Python 3.9 或更新版本**，不需要安装第三方 Python 包。在项目根目录运行：

```bash
python3 script/download_datasets.py
```

Windows 可将 `python3` 换成 `python`。脚本以自身所在项目定位默认目录，从其他工作目录调用也可使用。

下载源：[GitHub Release — datasets-v1](https://github.com/Ch-Jiale/Aletheia-datasets/releases/tag/datasets-v1)。无需 GitHub 账号。

也可从 Release 下载 `aletheia-dataset-downloader.zip`，解压后运行同一条命令。

脚本逐个下载，支持断点续传、失败重试，以及文件大小和 SHA-256 校验。
已存在且校验正确的文件会自动跳过；下载保存在 `.mp4.part` 文件中，校验通过后才替换目标文件。
如果下载中断，重新运行同一条命令即可。服务器不支持断点续传时，会自动从头下载该文件。

```bash
# 只检查本地视频是否完整，不访问网络
python3 script/download_datasets.py --verify-only

# 查看全部文件、大小和校验值
python3 script/download_datasets.py --list

# 指定保存位置
python3 script/download_datasets.py --output-dir /path/to/dataset

# 调整网络超时和每个视频的最大尝试次数
python3 script/download_datasets.py --timeout 120 --retries 5
```

成功退出码为 `0`；缺失、校验失败或下载失败为 `1`；手动中断为 `130`。
保存完整视频需要约 559 MiB 空间；修复已有损坏文件时还需容纳正在下载的临时文件。

## 目录结构

```text
CrossSight/dataset/
├── day_01/
│   ├── cam_00/  # hour_00.mp4, hour_01.mp4
│   ├── cam_01/  # hour_00.mp4, hour_01.mp4
│   └── cam_02/  # hour_00.mp4, hour_01.mp4
└── day_02/
    ├── cam_00/  # hour_00.mp4, hour_01.mp4
    ├── cam_01/  # hour_00.mp4, hour_01.mp4
    └── cam_02/  # hour_00.mp4, hour_01.mp4
```

`manifest.json` 记录从本地这 12 个视频计算出的大小和 SHA-256，确保下载得到相同文件。
视频仍由 `.gitignore` 排除，不随 Git 源码提交。

## 下载源与镜像

每个视频可在 `manifest.json` 的 `url` 中配置独立的 HTTP(S) 直链，例如 GitHub Release 附件地址。
下载地址必须直接返回视频内容，而非网盘预览或登录页面。

如果镜像保留了 `day_01/cam_00/hour_00.mp4` 等相对路径，可使用：

```bash
python3 script/download_datasets.py --base-url https://your-host.example/dataset
```

`--base-url` 会覆盖清单内的地址。公开视频无需 GitHub 账号或访问令牌。

