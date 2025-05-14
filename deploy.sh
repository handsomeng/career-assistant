#!/bin/bash

echo "==== 开始部署职业规划小助手 ===="

# 进入项目目录（注意修改成您服务器上的实际路径）
cd /home/ubuntu/career-assistant

# 拉取最新代码
echo "正在拉取最新代码..."
git pull

# 安装/更新依赖
echo "正在更新依赖..."
pip install -r requirements.txt

# 重启服务（根据您的实际情况修改）
echo "正在重启服务..."
# 如果您使用supervisor管理进程：
# sudo supervisorctl restart career_assistant

# 如果您使用systemd管理服务：
# sudo systemctl restart career-assistant.service

# 或者如果您是直接运行Python：
# pkill -f "python app.py"
# nohup python app.py > app.log 2>&1 &

echo "==== 部署完成 ====" 