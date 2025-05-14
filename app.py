from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import json
import requests
import os # 用于处理文件名和路径
from werkzeug.utils import secure_filename # 用于安全地处理上传的文件名
import pdfplumber  # 用于PDF解析
import docx        # 用于DOCX解析
import time

app = Flask(__name__, static_folder='.', static_url_path='') # 明确指定静态文件目录和URL路径
CORS(app)

# 确保上传文件夹存在
UPLOAD_FOLDER = './uploads' # 您可以指定服务器上的任何安全路径
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# DeepSeek API 配置 (安全警告：生产环境不要硬编码API Key)
DEEPSEEK_API_KEY = "sk-94ee67f1837740db9c8c9d0f2646b210"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, '职业规划小助手.html')

@app.route('/职业规划小助手.html')
def serve_html_directly():
    return send_from_directory(app.static_folder, '职业规划小助手.html')

# 辅助函数: 从DeepSeek API获取流式响应
def stream_deepseek_api(messages):
    response = requests.post(
        DEEPSEEK_API_URL,
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,  # 提高温度以加快生成速度
            "max_tokens": 2500,   # 控制生成长度
            "stream": True        # 启用流式输出
        },
        stream=True  # 使用requests的流式处理
    )
    
    if not response.ok:
        yield f"data: {json.dumps({'error': f'API错误: {response.status_code}'})}\n\n"
        return
    
    all_content = ""  # 用于累积完整内容
    
    for line in response.iter_lines():
        if line:
            line_text = line.decode('utf-8')
            
            # DeepSeek API流式响应格式处理
            if line_text.startswith('data: '):
                data_str = line_text[6:]  # 去掉 'data: ' 前缀
                
                if data_str == "[DONE]":
                    # 流结束，发送完整内容
                    yield f"data: {json.dumps({'done': True, 'full_content': all_content})}\n\n"
                    break
                
                try:
                    data = json.loads(data_str)
                    if 'choices' in data and len(data['choices']) > 0:
                        delta = data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            all_content += content
                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                except Exception as e:
                    print(f"解析流式响应时出错: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

# 辅助函数: 清理JSON字符串
def clean_json_string(json_str):
    # 去除可能包含的Markdown代码块符号
    if json_str.startswith('```') and json_str.endswith('```'):
        json_str = json_str.strip('`')
        
    # 尝试找到JSON块的开始和结束
    start_idx = json_str.find('{')
    end_idx = json_str.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        return json_str[start_idx:end_idx+1]
    return json_str

# 提取简历内容
def extract_resume_content(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    text = ""
    try:
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext == '.pdf':
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    
        elif file_ext == '.docx':
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
                
        else:
            text = f"不支持的文件格式: {file_ext}"
            
    except Exception as e:
        text = f"解析文件时出错: {str(e)}"
        
    return text

# 流式职业分析API
@app.route('/api/analyze/stream', methods=['POST'])
def stream_analyze_career():
    mbti = request.form.get('mbti', '未提供')
    city = request.form.get('city', '未提供')
    resume_content = "未上传简历"
    
    # 解析霍兰德测试答案
    holland_answers_str = request.form.get('holland_answers', '{}')
    try:
        holland_answers = json.loads(holland_answers_str)
    except:
        holland_answers = {}
    
    # 简化的霍兰德代码解析
    holland_code = {}
    for q, answer in holland_answers.items():
        if answer not in holland_code:
            holland_code[answer] = 0
        holland_code[answer] = holland_code[answer] + 1
    
    holland_summary = ", ".join([f"{code}:{count}" for code, count in holland_code.items()])
    
    # 处理上传的简历
    resume_file = request.files.get('resume')
    if resume_file and resume_file.filename:
        resume_content = extract_resume_content(resume_file)
        # 简化简历内容以加快API响应
        if len(resume_content) > 2000:
            resume_content = resume_content[:2000] + "...(已截断)"
    
    # 构建提示消息
    system_message = {
        "role": "system",
        "content": """你是专业的职业规划分析师。请基于用户的MBTI、霍兰德测试结果和简历内容进行分析。
你的任务是：
1. 提供整体分析和洞察(insight)，包括三个明确部分：
   - MBTI分析：分析MBTI类型与职业特质的关系
   - 霍兰德分析：分析霍兰德模型结果与职业兴趣的关系
   - 简历分析：分析简历显示的能力、技能和背景
2. 推荐5个最匹配的职业(recommendations)，每个包含ID、名称、简短描述和推荐理由。

请直接返回分析结果，不需要加入markdown标记。结果应包含以下内容：
- insight: 整体分析，明确分为MBTI分析、霍兰德分析和简历分析三部分
- recommendations: 包含5个职业推荐，每个有id、name、short_description和reason字段

保持分析精确但简洁，注重质量和实用性。"""
    }
    
    user_message = {
        "role": "user",
        "content": f"""请分析以下信息并给出职业规划建议：
- MBTI类型：{mbti}
- 所在城市：{city}
- 霍兰德测试结果：{holland_summary}
- 简历内容：{resume_content}

请注意，您的回复将被直接解析为JSON格式，因此请确保您的回复是有效的JSON内容。
"""
    }
    
    messages = [system_message, user_message]
    
    # 使用stream_with_context确保流式响应可以正确传输
    return Response(stream_with_context(stream_deepseek_api(messages)), 
                   mimetype='text/event-stream')

# 流式职业详情API
@app.route('/api/career-details/stream', methods=['POST'])
def stream_career_details():
    career_id = request.form.get('career_id', '')
    career_name = request.form.get('career_name', '未知职业')
    city = request.form.get('city', '未提供')
    mbti = request.form.get('mbti', '未提供')
    
    # 解析霍兰德测试结果和简历内容，与analyze_career类似
    holland_answers_str = request.form.get('holland_answers', '{}')
    try:
        holland_answers = json.loads(holland_answers_str)
    except:
        holland_answers = {}
    
    holland_code = {}
    for q, answer in holland_answers.items():
        if answer not in holland_code:
            holland_code[answer] = 0
        holland_code[answer] = holland_code[answer] + 1
    
    holland_summary = ", ".join([f"{code}:{count}" for code, count in holland_code.items()])
    
    resume_content = "未提供简历"
    resume_file = request.files.get('resume')
    if resume_file and resume_file.filename:
        resume_content = extract_resume_content(resume_file)
        if len(resume_content) > 1000:  # 简化简历内容
            resume_content = resume_content[:1000] + "...(已截断)"
    
    system_message = {
        "role": "system",
        "content": """你是专业的职业规划分析师，现在需要针对用户选择的特定职业提供详细分析。
根据用户的背景（MBTI、霍兰德测试、简历）以及所选职业，请提供以下详细内容：
1. name: 职业名称
2. salary_info: 该职业在用户所在城市的薪资范围和影响因素
3. development_plan: 该职业的发展路径和晋升规划
4. learning_resources: 进入和提升该职业所需的学习资源和证书
5. core_competencies: 该职业所需的核心能力和素质
6. daily_workflow: 该职业的日常工作内容和节奏

请直接以JSON格式返回上述内容，确保每个字段都有具体且有用的信息。不要返回没有内容的字段。"""
    }
    
    user_message = {
        "role": "user",
        "content": f"""请为以下职业提供详细分析：
- 职业：{career_name} (ID: {career_id})
- MBTI类型：{mbti}
- 所在城市：{city}
- 霍兰德测试结果：{holland_summary}
- 简历内容：{resume_content}

请以JSON格式直接返回结果，包含name、salary_info、development_plan、learning_resources、core_competencies和daily_workflow字段。"""
    }
    
    messages = [system_message, user_message]
    
    return Response(stream_with_context(stream_deepseek_api(messages)),
                   mimetype='text/event-stream')

# 保留原有的非流式API端点，以兼容旧版本
@app.route('/api/analyze', methods=['POST'])
def analyze_career():
    mbti = request.form.get('mbti', '未提供')
    city = request.form.get('city', '未提供')
    holland_answers_str = request.form.get('holland_answers', '{}')
    
    try:
        holland_answers_dict = json.loads(holland_answers_str)
    except json.JSONDecodeError:
        holland_answers_dict = {}
        print(f"无法解析霍兰德答案字符串: {holland_answers_str}")

    resume_file = request.files.get('resume')
    resume_content_summary = "未上传简历。"
    resume_text = ""
    original_filename = ""

    # 解析简历内容
    if resume_file and resume_file.filename:
        original_filename = secure_filename(resume_file.filename)
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        resume_file.save(file_path)
        
        try:
            if ext == 'pdf':
                # 使用pdfplumber提取PDF文本
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        extracted_text = page.extract_text()
                        if extracted_text:
                            resume_text += extracted_text + "\n\n"
            elif ext in ['doc', 'docx']:
                # 使用python-docx提取Word文本
                doc = docx.Document(file_path)
                for para in doc.paragraphs:
                    resume_text += para.text + "\n"
            else:
                resume_text = f"不支持的文件格式: {ext}"
                
            # 如果提取到内容，使用前1000个字符作为摘要
            if resume_text:
                resume_content_summary = resume_text[:1000] + ("..." if len(resume_text) > 1000 else "")
        except Exception as e:
            resume_content_summary = f"解析文件时出错: {str(e)}"

    # 简化的霍兰德测试结果分析 (R-现实型, I-研究型, A-艺术型, S-社会型, E-企业型, C-常规型)
    holland_codes = {'R': 0, 'I': 0, 'A': 0, 'S': 0, 'E': 0, 'C': 0}
    for q, answer in holland_answers_dict.items():
        if answer in holland_codes:
            holland_codes[answer] += 1
    
    # 找出得分最高的三种类型
    top_holland = sorted(holland_codes.items(), key=lambda x: x[1], reverse=True)[:3]
    holland_summary = ", ".join([f"{code}型({score}分)" for code, score in top_holland if score > 0])
    
    # 构建和AI模型的对话消息
    system_message = {
        "role": "system",
        "content": """你是专业的职业规划分析师。请基于用户的MBTI、霍兰德测试结果和简历内容进行分析。
你的回答必须是JSON格式，包含以下两部分：
1. insight: 对用户的整体分析，包括MBTI分析、霍兰德模型分析和简历分析
2. recommendations: 推荐5个职业，每个职业必须包含以下字段：
   - id: 唯一标识符（数字）
   - name: 职业名称
   - short_description: 简短描述
   - reason: 推荐原因
   - percentage: 匹配度百分比（1-100的数字）

确保按照上述格式返回，不要添加任何其他格式如markdown。只返回纯JSON格式内容。"""
    }
    
    user_message = {
        "role": "user",
        "content": f"""请分析以下信息并给出职业规划建议：
- MBTI类型：{mbti}
- 所在城市：{city}
- 霍兰德测试结果：{holland_summary}
- 简历内容：{resume_content_summary}

请注意，您的回复将被直接解析为JSON格式，因此请确保您的回复是有效的JSON，并且不要使用markdown格式(如```json)。
"""
    }
    
    # 调用DeepSeek API
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [system_message, user_message],
                "temperature": 0.7,
                "max_tokens": 3000
            }
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"API调用失败: {response.status_code}", "detail": response.text}), 500
        
        api_response = response.json()
        if "choices" not in api_response or len(api_response["choices"]) == 0:
            return jsonify({"error": "API返回无效响应", "detail": api_response}), 500
        
        ai_response = api_response["choices"][0]["message"]["content"]
        
        # 清理并解析JSON响应
        try:
            cleaned_json = clean_json_string(ai_response)
            result = json.loads(cleaned_json)
            
            # 验证结果格式
            if not isinstance(result, dict):
                return jsonify({"error": "AI分析结果格式错误", "short_description": "返回的不是一个对象"}), 500
            
            if "insight" not in result or "recommendations" not in result:
                return jsonify({"error": "AI分析结果格式错误", "short_description": "缺少必要的字段"}), 500
            
            if not isinstance(result["recommendations"], list):
                return jsonify({"error": "AI分析结果格式错误", "short_description": "recommendations不是数组"}), 500
            
            # 验证职业推荐数据完整性
            for rec in result["recommendations"]:
                if not all(k in rec for k in ["id", "name", "short_description", "reason"]):
                    return jsonify({"error": "AI分析结果格式错误", "short_description": "AI返回的部分职业数据不完整。"}), 500
            
            return jsonify(result)
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {ai_response}")
            return jsonify({"error": "AI分析响应非JSON", "short_description": str(e)}), 500
            
    except Exception as e:
        print(f"API调用出错: {str(e)}")
        return jsonify({"error": "调用AI分析失败", "short_description": str(e)}), 500

@app.route('/api/career-details', methods=['POST'])
def get_career_details():
    career_id = request.form.get('career_id', '')
    career_name = request.form.get('career_name', '未知职业')
    city = request.form.get('city', '未提供')
    mbti = request.form.get('mbti', '未提供')
    
    holland_answers_str = request.form.get('holland_answers', '{}')
    try:
        holland_answers_dict = json.loads(holland_answers_str)
    except json.JSONDecodeError:
        holland_answers_dict = {}
    
    # 处理简历文件
    resume_file = request.files.get('resume')
    resume_content = "未上传简历"
    if resume_file and resume_file.filename:
        filename = secure_filename(resume_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        resume_file.save(file_path)
        
        try:
            # 根据文件扩展名处理
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if ext == 'pdf':
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        extracted_text = page.extract_text()
                        if extracted_text:
                            resume_content += extracted_text + "\n\n"
            elif ext in ['doc', 'docx']:
                doc = docx.Document(file_path)
                for para in doc.paragraphs:
                    resume_content += para.text + "\n"
            else:
                resume_content = f"不支持的文件格式: {ext}"
        except Exception as e:
            resume_content = f"解析文件时出错: {str(e)}"
    
    # 构建霍兰德测试结果摘要
    holland_codes = {'R': 0, 'I': 0, 'A': 0, 'S': 0, 'E': 0, 'C': 0}
    for q, answer in holland_answers_dict.items():
        if answer in holland_codes:
            holland_codes[answer] += 1
    
    top_holland = sorted(holland_codes.items(), key=lambda x: x[1], reverse=True)[:3]
    holland_summary = ", ".join([f"{code}型({score}分)" for code, score in top_holland if score > 0])
    
    # 构建提示消息
    system_message = {
        "role": "system",
        "content": """你是专业的职业规划分析师，现在需要针对用户选择的特定职业提供详细分析。
根据用户的背景（MBTI、霍兰德测试、简历）以及所选职业，请以JSON格式返回以下详细内容：
1. name: 职业名称
2. salary_info: 该职业在用户所在城市的薪资范围和影响因素
3. development_plan: 该职业的发展路径和晋升规划，以HTML格式呈现，可使用<ul><li>等标签
4. learning_resources: 进入和提升该职业所需的学习资源和证书，以HTML格式呈现
5. core_competencies: 该职业所需的核心能力和素质，以HTML格式呈现
6. daily_workflow: 该职业的日常工作内容和节奏，以HTML格式呈现

确保JSON格式有效，不要使用markdown代码块(如```json)。"""
    }
    
    user_message = {
        "role": "user",
        "content": f"""请为以下职业提供详细分析：
- 职业：{career_name} (ID: {career_id})
- MBTI类型：{mbti}
- 所在城市：{city}
- 霍兰德测试结果：{holland_summary}
- 简历内容：{resume_content}"""
    }
    
    # 调用DeepSeek API
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [system_message, user_message],
                "temperature": 0.7,
                "max_tokens": 3000
            }
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"API调用失败: {response.status_code}"}), 500
        
        api_response = response.json()
        if "choices" not in api_response or len(api_response["choices"]) == 0:
            return jsonify({"error": "API返回无效响应"}), 500
        
        ai_response = api_response["choices"][0]["message"]["content"]
        
        # 清理并解析JSON响应
        try:
            cleaned_json = clean_json_string(ai_response)
            result = json.loads(cleaned_json)
            
            # 确保基本字段存在，如果不存在则添加默认值
            if "name" not in result:
                result["name"] = career_name
                
            return jsonify(result)
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"原始响应: {ai_response}")
            return jsonify({
                "error": "API响应解析失败", 
                "name": career_name,
                "salary_info": "无法获取薪资信息",
                "development_plan": "<p>获取职业发展路径信息失败</p>",
                "learning_resources": "<p>获取学习资源信息失败</p>",
                "core_competencies": "<p>获取核心能力信息失败</p>",
                "daily_workflow": "<p>获取日常工作流程信息失败</p>"
            })
            
    except Exception as e:
        print(f"API调用出错: {str(e)}")
        return jsonify({
            "error": str(e), 
            "name": career_name,
            "salary_info": "调用AI分析时出错",
            "development_plan": f"<p>错误: {str(e)}</p>",
            "learning_resources": "<p>请稍后再试</p>",
            "core_competencies": "<p>请稍后再试</p>",
            "daily_workflow": "<p>请稍后再试</p>"
        })

if __name__ == '__main__':
    # 确保在 /www/wwwroot/wm/ 目录下运行此脚本
    # 或者用绝对路径指定日志文件位置
    # logging.basicConfig(filename='app.log', level=logging.DEBUG) # 可以取消注释来记录日志到文件
    app.run(host='0.0.0.0', port=5000) 