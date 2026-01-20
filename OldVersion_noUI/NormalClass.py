import requests
import json
import time
import datetime
import re
import urllib.parse

# 注意：这个程序是AI写的！！！
# Powered by Qwen-3

# ================== 快速配置区域 ==================
# 你只需要修改快速配置区域（如果你不是python大神的话）

# 请求头部分
UserAgentTypeIn = "*****"  # ← 修改这里：你的浏览器UA（请阅读说明）
AcceptLanguage = "*****"   # ← 修改这里：你的浏览器的AcceptLanguage（请阅读说明）
BatchID = "*****"          # ← 修改这里：你的batchId
CookieIsHere = "*****"     # ← 修改这里：你的完整cookie

campus = "S"  # ← 南校区就是S，北校区可能是N（？）

# 每个课程是一个字典，支持不同类别和搜索关键词
# {
#     "teachingClassType": "TJKC",    # ← 修改：课程类型（如COMPULSORY, PE, FANYUE等）
#     "KEY": "英语",                   # ← 修改：搜索关键词（老师名、课名、课程号等）
#     "clazzType": "TJKC"             # ← 修改：提交时的clazzType（一般等于teachingClassType）
# },
COURSES_TO_ENROLL = [
    {
        "teachingClassType": "TYKC",
        "KEY": "***",
        "clazzType": "TYKC"
    },
    {
        "teachingClassType": "TJKC",
        "KEY": "***",
        "clazzType": "TJKC"
    },
    {
        "teachingClassType": "TJKC",
        "KEY": "***",
        "clazzType": "TJKC"
    }
    # 可继续添加更多课程...
]

# BetweenTime是每次尝试选课之间间隔的时长，WaitTime是程序完毕后总结报告的延时,TryTimes是尝试次数（举例若为2则失败后再额外尝试一次）
BetweenTime = 1
TryTimes = 2
WaitTime = 1
SetTimeAndStart = 0  # 是否定时开启，是则设置为1
# 关于定时：仅当天可用，若已过时则立即启动，否则等到时间再启动

now = datetime.datetime.now()
target = now.replace(hour=8, minute=0, second=0, microsecond=0)  # 定时开启的时间，时分秒毫秒，精确到毫秒

# ================== 快速配置区域结束 ==================


match = re.search(r'Authorization=([^;]+)', CookieIsHere)
if match:
    Author = match.group(1)  # group(1) 是括号捕获的内容
else:
    print("你的cookie有问题。请关闭本窗口并检查。")
    input()

CHECK_URL = "https://xk.xidian.edu.cn/xsxk/elective/clazz/list"
COURSE_URL = "https://xk.xidian.edu.cn/xsxk/elective/clazz/add"

HEADERS_CHECK = {
    "Host": "xk.xidian.edu.cn",
    "User-Agent": UserAgentTypeIn,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": AcceptLanguage,
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Content-Type": "application/json;charset=utf-8",
    "Authorization": Author,
    "batchId": BatchID,
    "Origin": "https://xk.xidian.edu.cn",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Referer": "https://xk.xidian.edu.cn/xsxk/elective/grablessons?batchId="+BatchID,
    "Cookie": CookieIsHere,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0"
}

HEADERS_COURSE = HEADERS_CHECK.copy()
HEADERS_COURSE["Content-Type"] = "application/x-www-form-urlencoded"

# 跟踪每门课的状态
course_status = {}

def monitor_time_start():
    # 计算距离时间还有多久

    if now > target:
        print("当前时间已过")
    else:
        wait_seconds = (target - now).total_seconds()
        print(f"开始等待 {wait_seconds} 秒...")
        time.sleep(wait_seconds)
        print("时间到！执行代码...")

# ================== 抢课请求 ==================
def submit_enrollment(clazzId, secretVal, clazzType, course_key):
    """尝试抢一门课，最多重试一次"""
    form_data = {
        "clazzType": clazzType,
        "clazzId": clazzId,
        "secretVal": secretVal
    }
    body = urllib.parse.urlencode(form_data)

    for attempt in range(1, TryTimes+1):  # 尝试次数
        try:
            print(f"🎯 [{course_key}] 第 {attempt} 次抢课请求...")
            response = requests.post(COURSE_URL, headers=HEADERS_COURSE, data=body, timeout=10)

            if response.status_code == 200:
                try:
                    result = response.json()
                    msg = result.get("msg", "未知响应")
                    print(f"💡 [{course_key}] 服务器返回: {msg}")

                    if result.get("code") in [200, "200"]:
                        print(f"✅ [{course_key}] 恭喜！抢课成功！")
                        return True
                    elif "已选" in msg or "重复" in msg:
                        print(f"⚠️ [{course_key}] 你可能已经选过这门课了")
                        return True
                    else:
                        if attempt < TryTimes:
                            print(f"⚠️ [{course_key}] 第 {attempt} 次失败，正在重试...")
                            time.sleep(BetweenTime)
                        else:
                            print(f"❌ [{course_key}] 所有尝试均失败")
                except json.JSONDecodeError:
                    print(f"⚠️ [{course_key}] 非法 JSON 响应:", response.text)
            else:
                print(f"❌ [{course_key}] 请求失败，状态码: {response.status_code}")
                if attempt < TryTimes:
                    time.sleep(BetweenTime)
        except requests.RequestException as e:
            print(f"❌ [{course_key}] 请求异常: {e}")
            if attempt < TryTimes:
                time.sleep(BetweenTime)
    return False  # 两次都失败

# ================== 单门课程监控与抢课逻辑 ==================
def monitor_and_enroll(course_config, course_key):
    """监控并尝试抢指定的一门课"""
    if course_status[course_key]["done"]:
        return

    try:
        # 构造请求数据
        data_check = {
            "teachingClassType": course_config["teachingClassType"],
            "pageNumber": 1,
            "pageSize": 10,
            "orderBy": "",
            "campus": campus,
            "KEY": course_config["KEY"]
        }

        response = requests.post(CHECK_URL, headers=HEADERS_CHECK, json=data_check, timeout=10)
        if response.status_code != 200:
            print(f"❌ [{course_key}] 请求失败: {response.status_code}")
            return

        json_data = response.json()
        if json_data.get("code") != 200:
            print(f"❌ [{course_key}] 接口错误: {json_data.get('msg')}")
            return

        rows = json_data.get("data", {}).get("rows", [])
        if not rows:
            print(f"⚠️ [{course_key}] 未查到课程")
            return

        tc_list = rows[0].get("tcList", [])
        if not tc_list:
            print(f"⚠️ [{course_key}] 无教学班信息")
            return

        teaching_class = tc_list[0]  # 取第一个教学班
        selected = teaching_class.get("numberOfSelected")
        capacity = teaching_class.get("classCapacity")
        clazzId = teaching_class.get("JXBID") or teaching_class.get("teachingClassID")
        secretVal = teaching_class.get("secretVal")

        if None in (selected, capacity, clazzId, secretVal):
            print(f"⚠️ [{course_key}] 数据不完整，跳过")
            return

        print(f"📊 [{course_key}] 当前 {selected}/{capacity} 人")

        success = submit_enrollment(clazzId, secretVal, course_config["clazzType"], course_key)
        course_status[course_key]["done"] = True
        if success:
            print(f"🎉 [{course_key}] 抢课完成！")
        else:
            print(f"🚫 [{course_key}] 抢课失败，跳过")

    except Exception as e:
        print(f"❌ [{course_key}] 检查过程异常: {e}")

# ================== 主循环 ==================
if __name__ == "__main__":

    if match:
        Author = match.group(1)  # group(1) 是括号捕获的内容
    else:
        print("你的cookie有问题。按任意键退出。")
        input()

    if SetTimeAndStart:
        monitor_time_start()

    print("🔍 开始准备对多门课程进行自动抢课...")

    # 初始化状态
    for i, course in enumerate(COURSES_TO_ENROLL):
        key = f"课程{i+1}: {course['KEY']}"
        course_status[key] = {"done": False, "config": course}

    # 循环监控，直到所有课程都完成
    while True:
        all_done = True
        for course_key, status in course_status.items():
            if not status["done"]:
                all_done = False
                monitor_and_enroll(status["config"], course_key)
        if all_done:
            print("✅ 所有课程抢课流程结束，程序退出。")
            break
        time.sleep(WaitTime)  # 每1.5秒轮询一次
