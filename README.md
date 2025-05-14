# 职业规划小助手

这是一个基于AI的职业规划助手，通过分析用户的MBTI性格类型、霍兰德职业兴趣测试结果以及个人简历，为用户提供定制化的职业发展建议。

## 主要功能

- MBTI性格分析
- 霍兰德职业兴趣测评
- 简历技能分析
- AI职业匹配推荐
- 详细职业发展路径分析

## 技术栈

- 前端：HTML, CSS, JavaScript
- 后端：Python Flask
- AI：基于大型语言模型

## 如何使用

1. 克隆仓库
   ```bash
   git clone https://github.com/handsomeng/career-assistant.git
   cd career-assistant
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 启动服务器
   ```bash
   python app.py
   ```

4. 访问 `http://localhost:5000`

## Git版本管理流程

我们使用Git进行版本管理，以下是推荐的工作流程：

1. **克隆仓库**
   ```bash
   git clone https://github.com/handsomeng/career-assistant.git
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **提交更改**
   ```bash
   git add .
   git commit -m "描述你的更改"
   ```

4. **推送到远程仓库**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **创建合并请求**
   在GitHub上创建Pull Request，将你的功能分支合并到main分支

6. **版本标签**
   发布新版本时，使用标签标记
   ```bash
   git tag -a v1.0.0 -m "版本1.0.0发布"
   git push origin v1.0.0
   ```

## 服务器部署

### 初次部署

1. 在服务器上安装Git和Python
   ```bash
   sudo apt update
   sudo apt install git python3 python3-pip
   ```

2. 克隆仓库
   ```bash
   git clone https://github.com/handsomeng/career-assistant.git
   cd career-assistant
   pip install -r requirements.txt
   ```

3. 设置系统服务
   ```bash
   # 复制服务文件到systemd目录
   sudo cp career-assistant.service /etc/systemd/system/
   
   # 启用并启动服务
   sudo systemctl daemon-reload
   sudo systemctl enable career-assistant.service
   sudo systemctl start career-assistant.service
   ```

### 自动化部署

使用部署脚本进行更新：

1. 确保deploy.sh具有执行权限
   ```bash
   chmod +x deploy.sh
   ```

2. 运行部署脚本
   ```bash
   ./deploy.sh
   ```

## 版本历史

- v1.0.0 - 初始版本
- v1.0.1 - 添加部署脚本和GitHub工作流
- v1.1.0 - 添加项目主页和系统服务配置

## 贡献

欢迎提交Pull Request或Issue来改进这个项目。
