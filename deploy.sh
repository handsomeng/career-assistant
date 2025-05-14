#!/bin/bash

echo "==== 开始部署职业规划小助手 ===="
echo "$(date) - 开始部署" >> /home/ubuntu/deploy.log

# 进入项目目录（注意修改成您服务器上的实际路径）
cd /home/ubuntu/career-assistant

# 拉取最新代码
echo "正在拉取最新代码..."
git pull

# 安装/更新依赖
echo "正在更新依赖..."
pip install -r requirements.txt

# 重启服务
echo "正在重启服务..."
# 如果使用systemd管理服务
sudo systemctl restart career-assistant.service
echo "服务已重启: $(date)" >> /home/ubuntu/deploy.log

# 检查服务状态
sleep 2
SERVICE_STATUS=$(sudo systemctl is-active career-assistant.service)
if [ "$SERVICE_STATUS" = "active" ]; then
    echo "服务已成功重启!"
    echo "$(date) - 部署成功" >> /home/ubuntu/deploy.log
else
    echo "警告: 服务可能未正常启动，请检查日志"
    echo "$(date) - 部署异常，服务未正常启动" >> /home/ubuntu/deploy.log
fi

echo "==== 部署完成 ====" 