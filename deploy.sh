#!/bin/bash

# 获取脚本所在的绝对路径
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LOG_FILE="$SCRIPT_DIR/deploy.log"

echo "==== 开始部署职业规划小助手 ===="
echo "$(date) - 开始部署" >> "$LOG_FILE"

# 进入项目目录
cd "$SCRIPT_DIR"
if [ $? -ne 0 ]; then
    echo "错误：无法进入项目目录 $SCRIPT_DIR" >> "$LOG_FILE"
    echo "错误：无法进入项目目录 $SCRIPT_DIR. 部署中止."
    exit 1
fi

# 尝试加载环境变量，以确保 pip/pip3 在 PATH 中
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
elif [ -f /etc/profile ]; then
    source /etc/profile
fi

# 拉取最新代码
echo "正在拉取最新代码..."
git pull
if [ $? -ne 0 ]; then
    echo "错误：git pull 失败" >> "$LOG_FILE"
    echo "错误：git pull 失败. 部署中止."
    exit 1
fi

# 安装/更新依赖
echo "正在更新依赖..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo "错误: pip 和 pip3 命令都未找到。请先安装 pip。" >> "$LOG_FILE"
    echo "错误: pip 和 pip3 命令都未找到。请先安装 pip。部署中止."
    exit 1
fi
if [ $? -ne 0 ]; then
    echo "错误：依赖安装失败 (pip install -r requirements.txt)" >> "$LOG_FILE"
    echo "错误：依赖安装失败. 部署中止."
    # 注意：某些情况下，即使部分依赖安装失败，服务仍可能启动，但这里选择中止
    # exit 1 # 可以根据需要取消注释此行
fi


# 重启服务
echo "正在重启服务..."
# 如果使用systemd管理服务
sudo systemctl restart career-assistant.service
if [ $? -ne 0 ]; then
    echo "错误：无法执行 sudo systemctl restart career-assistant.service。请检查 systemd 服务配置和 sudo 权限。" >> "$LOG_FILE"
    # 不直接退出，但记录错误
fi
echo "服务已尝试重启: $(date)" >> "$LOG_FILE"

# 检查服务状态
sleep 2 # 等待服务启动
SERVICE_STATUS=$(sudo systemctl is-active career-assistant.service)
if [ "$SERVICE_STATUS" = "active" ]; then
    echo "服务已成功启动!"
    echo "$(date) - 部署成功，服务状态: $SERVICE_STATUS" >> "$LOG_FILE"
else
    echo "警告: 服务当前状态为 '$SERVICE_STATUS'，可能未正常启动。请检查日志: journalctl -u career-assistant.service 和 $LOG_FILE"
    echo "$(date) - 部署完成，但服务状态异常: $SERVICE_STATUS" >> "$LOG_FILE"
fi

echo "==== 部署完成 ====" 