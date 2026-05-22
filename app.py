from flask import Flask, request, jsonify
from zhipuai import ZhipuAI
import json
import os
from datetime import datetime

app = Flask(__name__)

# 你的智谱AI API Key，已经帮你填好了
ZHIPU_API_KEY = "b7ccb76aa2fc4d4e9ed20cd8d596334a.kxromGBI0dyhnHAy"
client = ZhipuAI(api_key=ZHIPU_API_KEY)

# 全局记忆系统
memory = {
    "user_info": {
        "name": "李曦",
        "target_school": "上海交通大学",
        "target_major": "电气专硕",
        "exam_subjects": ["政治", "英语二", "数学二", "电路"],
        "daily_study_hours": 10,
        "start_time": "7:00",
        "end_time": "22:30",
        "weak_subjects": ["数学二", "电路"]
    },
    "plans": {
        "quarterly": {},
        "monthly": {},
        "weekly": {},
        "daily": {}
    },
    "completion_history": [],
    "current_plan": ""
}

@app.route('/generate-daily-plan', methods=['POST'])
def generate_daily_plan():
    """生成每日学习日程"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    yesterday_completion = None
    if memory["completion_history"]:
        yesterday_completion = memory["completion_history"][-1]
    
    prompt = f"""
    你是一个严格但专业的考研规划师。请根据以下信息生成{today}的详细学习日程：
    
    【个人基本信息】
    目标院校：{memory['user_info']['target_school']}
    目标专业：{memory['user_info']['target_major']}
    考试科目：{', '.join(memory['user_info']['exam_subjects'])}
    每日可学习时长：{memory['user_info']['daily_study_hours']}小时
    学习时间：{memory['user_info']['start_time']} - {memory['user_info']['end_time']}
    薄弱科目：{', '.join(memory['user_info']['weak_subjects'])}
    
    【昨天完成情况】
    {json.dumps(yesterday_completion, ensure_ascii=False) if yesterday_completion else "第一天学习，无历史数据"}
    
    【要求】
    1. 严格按照番茄工作法：学习50分钟，休息10分钟
    2. 上午安排数学和专业课（大脑最清醒的时间）
    3. 下午安排英语和政治
    4. 晚上安排复盘和错题整理
    5. 中午12:00-14:00是午饭和午休时间
    6. 晚饭18:00-19:00
    7. 每个任务要具体到"做什么、做多少"，不要写"复习数学"这种模糊的内容
    8. 输出格式：
    7:00-7:50 任务内容
    8:00-8:50 任务内容
    ...
    """
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2000
    )
    
    daily_plan = response.choices[0].message.content
    memory["plans"]["daily"][today] = daily_plan
    memory["current_plan"] = daily_plan
    
    return jsonify({
        "success": True,
        "plan": f"📅 {today} 考研学习日程\n\n{daily_plan}\n\n💪 加油！今天也要全力以赴！"
    })

@app.route('/adjust-plan', methods=['POST'])
def adjust_plan():
    """根据用户输入调整当前日程"""
    data = request.json
    user_input = data.get('user_input', '')
    
    if not memory["current_plan"]:
        return jsonify({
            "success": False,
            "message": "还没有生成今日日程，请先等待早上7点的推送，或者发送'生成今日日程'手动生成"
        })
    
    prompt = f"""
    当前日程：
    {memory['current_plan']}
    
    用户修改要求：{user_input}
    
    请根据用户要求修改日程，保持整体结构和番茄工作法不变，只修改相关部分。
    输出修改后的完整日程，不要有其他解释。
    """
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=2000
    )
    
    adjusted_plan = response.choices[0].message.content
    memory["current_plan"] = adjusted_plan
    today = datetime.now().strftime("%Y-%m-%d")
    memory["plans"]["daily"][today] = adjusted_plan
    
    return jsonify({
        "success": True,
        "plan": f"✅ 日程已修改\n\n{adjusted_plan}"
    })

@app.route('/auto-reschedule', methods=['POST'])
def auto_reschedule():
    """根据今日完成情况自动重排未来计划"""
    data = request.json
    today_completion = data.get('completion', {})
    
    today_completion["date"] = datetime.now().strftime("%Y-%m-%d")
    memory["completion_history"].append(today_completion)
    
    prompt = f"""
    今日完成情况：{json.dumps(today_completion, ensure_ascii=False)}
    
    请分析：
    1. 哪些任务没有完成，原因是什么
    2. 如何将未完成的任务合理安排到未来3天
    3. 给出调整后的未来3天大致计划
    4. 给出明天的学习建议
    
    语气要鼓励为主，但也要指出问题。
    """
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=1500
    )
    
    return jsonify({
        "success": True,
        "report": f"📊 今日学习复盘\n\n{response.choices[0].message.content}"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查，防止Render休眠"""
    return "OK"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
