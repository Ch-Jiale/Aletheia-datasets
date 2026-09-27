# Aletheia datasets

12 个 MP4 视频，共 **586,000,478 字节（约 559 MiB）**，保留 `day_XX/cam_XX/hour_XX.mp4` 结构。

## 一键下载

需要 Python 3.9+，不需要第三方 Python 包或 GitHub 账号：

```bash
git clone https://github.com/Ch-Jiale/Aletheia-datasets.git
cd Aletheia-datasets
python3 script/download_datasets.py
```

默认保存到当前仓库的 `CrossSight/dataset/`。如果已经有 Aletheia 项目，可以指定项目的数据目录：

```bash
python3 script/download_datasets.py --output-dir /path/to/Aletheia/CrossSight/dataset
```

也可以从 [Release](https://github.com/Ch-Jiale/Aletheia-datasets/releases/tag/datasets-v1) 下载 `aletheia-dataset-downloader.zip`，解压后运行 `python3 script/download_datasets.py`。

支持断点续传、失败重试、自动跳过完整文件，以及 SHA-256 校验。仅校验现有视频：

```bash
python3 script/download_datasets.py --verify-only
```

Windows 可将 `python3` 换成 `python`。更多选项见 [下载说明](datasets/README.md)。

## 文件说明

- `datasets/manifest.json`：12 个视频的下载地址、精确字节数和 SHA-256。
- `script/download_datasets.py`：仅依赖 Python 标准库的下载器。
- 视频通过 GitHub Release 附件分发，不保存在 Git 历史中。

