import requests
import json
import time
import urllib.parse

# 注意：这个程序是AI写的！！！
# Powered by Qwen-3

# 你需要修改第22\23\27\28行，以及40行以下的字典

# ================== 配置 ==================
CHECK_URL = "https://xk.xidian.edu.cn/xsxk/elective/clazz/list"
COURSE_URL = "https://xk.xidian.edu.cn/xsxk/elective/clazz/add"

HEADERS_CHECK = {
    "Host": "xk.xidian.edu.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Content-Type": "application/json;charset=utf-8",
    "Authorization": "*******",         # ← 修改这里：你的Authorization
    "batchId": "*******",               # ← 修改这里：你的batchId
    "Origin": "https://xk.xidian.edu.cn",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Referer": "https://xk.xidian.edu.cn/xsxk/elective/grablessons?batchId=*******",  # ← 修改batchId
    "Cookie": "Authorization=*******; route=*******",  # ← 修改这里：完整的Cookie
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0"
}

HEADERS_COURSE = HEADERS_CHECK.copy()
HEADERS_COURSE["Content-Type"] = "application/x-www-form-urlencoded"

# ================== 多门课程配置 ==================
# 每个课程是一个字典，支持不同类别和搜索关键词
COURSES_TO_ENROLL = [
    {
        "teachingClassType": "****",   # ← 修改：课程类型（如COMPULSORY, PE, FANYUE等）
        "KEY": "*******",                   # ← 修改：搜索关键词（老师名、课名、课程号等）
        "clazzType": "****"          # ← 修改：提交时的clazzType
    },
    {
        "teachingClassType": "****",
        "KEY": "*******",
        "clazzType": "****"
    },
    {
        "teachingClassType": "****",
        "KEY": "*******",
        "clazzType": "****"
    }
    # 可继续添加更多课程...
]

# 跟踪每门课的状态
course_status = {}

# ================== 抢课请求 ==================
def submit_enrollment(clazzId, secretVal, clazzType, course_key):
    """尝试抢一门课，最多重试一次"""
    form_data = {
        "clazzType": clazzType,
        "clazzId": clazzId,
        "secretVal": secretVal
    }
    body = urllib.parse.urlencode(form_data)

    for attempt in range(1, 3):  # 最多尝试2次
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
                        if attempt < 2:
                            print(f"⚠️ [{course_key}] 第 {attempt} 次失败，正在重试...")
                            time.sleep(0.5)
                        else:
                            print(f"❌ [{course_key}] 两次尝试均失败")
                except json.JSONDecodeError:
                    print(f"⚠️ [{course_key}] 非法 JSON 响应:", response.text)
            else:
                print(f"❌ [{course_key}] 请求失败，状态码: {response.status_code}")
                if attempt < 2:
                    time.sleep(0.5)
        except requests.RequestException as e:
            print(f"❌ [{course_key}] 请求异常: {e}")
            if attempt < 2:
                time.sleep(0.5)
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
            "campus": "S",
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

        if selected < capacity:
            print(f"🟢 [{course_key}] 发现空位！尝试抢课 → {clazzId}")
            success = submit_enrollment(clazzId, secretVal, course_config["clazzType"], course_key)
            course_status[course_key]["done"] = True
            if success:
                print(f"🎉 [{course_key}] 抢课完成！")
            else:
                print(f"🚫 [{course_key}] 抢课失败，跳过")
        else:
            print(f"🟡 [{course_key}] 已满员，继续监控...")

    except Exception as e:
        print(f"❌ [{course_key}] 检查过程异常: {e}")

# ================== 主循环 ==================
if __name__ == "__main__":
    print("🔍 开始监控多门课程，发现空位自动抢课...")

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
        time.sleep(0.5)  # 每1.5秒轮询一次