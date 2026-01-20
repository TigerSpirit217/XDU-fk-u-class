# normal_logic.py
import requests
import json
import time
import datetime
import re
import urllib.parse
from typing import Dict, Any, Callable


# ================== 核心抢课逻辑（适配 GUI 调用） ==================

def run_normal_class(config: Dict[str, Any], log_callback: Callable[[str], None], stop_flag: Callable[[], bool]):
    """
    执行普通/体育课程自动抢课（支持多门）

    :param config: 配置字典，包含以下字段：
        - UserAgent (str)
        - AcceptLanguage (str)
        - BatchID (str)
        - Cookie (str)
        - campus (str, 默认 "S")
        - WaitTime (int, 轮询间隔秒数)
        - courses (List[Dict]): 每个元素含 teachingClassType, KEY, clazzType
        - TryTimes (int, 默认 2)
        - BetweenTime (int, 默认 1)
        - SetTimeAndStart (int, 默认 0)
        - target_hour (int, 默认 8)
        - target_minute (int, 默认 0)

    :param log_callback: 日志输出回调函数，如 log(msg)
    :param stop_flag: 停止标志回调，返回 True 表示应停止
    """

    # ===== 1. 从 config 提取必要参数 =====
    UserAgentTypeIn = config.get("UserAgent", "").strip()
    AcceptLanguage = config.get("AcceptLanguage", "").strip()
    BatchID = config.get("BatchID", "").strip()
    CookieIsHere = config.get("Cookie", "").strip()
    campus = config.get("campus", "S")
    courses = config.get("courses", [])
    WaitTime = config.get("WaitTime", config.get("BetweenTime", 5))

    # ===== 2. 预留但 UI 未提供的参数（使用默认值）=====
    TryTimes = config.get("TryTimes", 2)
    BetweenTime = config.get("BetweenTime", 1)
    SetTimeAndStart = config.get("SetTimeAndStart", 0)
    target_hour = config.get("target_hour", 8)
    target_minute = config.get("target_minute", 0)
    target_second = config.get("target_second", 0)

    # ===== 3. 验证 Cookie =====
    match = re.search(r'Authorization=([^;]+)', CookieIsHere)
    if not match:
        log_callback("❌ 你的 cookie 有问题，请检查。")
        return
    Author = match.group(1)

    # ===== 4. 构造请求头 =====
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
        "Referer": f"https://xk.xidian.edu.cn/xsxk/elective/grablessons?batchId={BatchID}",
        "Cookie": CookieIsHere,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0"
    }
    HEADERS_COURSE = HEADERS_CHECK.copy()
    HEADERS_COURSE["Content-Type"] = "application/x-www-form-urlencoded"

    # ===== 5. 定时启动逻辑（若启用）=====
    if SetTimeAndStart == 1:
        now = datetime.datetime.now()
        target = now.replace(hour=target_hour, minute=target_minute, second=target_second, microsecond=0)
        if now < target:
            wait_seconds = (target - now).total_seconds()
            log_callback(f"🕒 当前未到设定时间，等待 {wait_seconds:.1f} 秒至 {target_hour}:{target_minute:02d}:{target_second:.1f}...")
            # 分段等待以响应 stop_flag
            waited = 0
            while waited < wait_seconds and not stop_flag():
                sleep_sec = min(1, wait_seconds - waited)
                time.sleep(sleep_sec)
                waited += sleep_sec
            if stop_flag():
                log_callback("🛑 用户中止，定时等待已取消。")
                return
        else:
            log_callback("⏰ 设定时间已过，立即开始抢课。")

    # ===== 6. 初始化课程状态 =====
    course_status = {}
    for i, course in enumerate(courses):
        key = f"课程{i + 1}: {course['KEY']}"
        course_status[key] = {"done": False, "config": course}

    # ===== 7. 辅助函数定义 =====
    def submit_enrollment(clazzId, secretVal, clazzType, course_key):
        """尝试抢一门课，最多重试 TryTimes 次"""
        form_data = {
            "clazzType": clazzType,
            "clazzId": clazzId,
            "secretVal": secretVal
        }
        body = urllib.parse.urlencode(form_data)
        for attempt in range(1, TryTimes + 1):
            if stop_flag():
                return False
            try:
                log_callback(f"🎯 [{course_key}] 第 {attempt} 次抢课请求...")
                response = requests.post(COURSE_URL, headers=HEADERS_COURSE, data=body, timeout=10)
                if response.status_code == 200:
                    try:
                        result = response.json()
                        msg = result.get("msg", "未知响应")
                        log_callback(f"💡 [{course_key}] 服务器返回: {msg}")
                        if result.get("code") in [200, "200"]:
                            log_callback(f"✅ [{course_key}] 恭喜！抢课成功！")
                            return True
                        elif "已选" in msg or "重复" in msg:
                            log_callback(f"⚠️ [{course_key}] 你可能已经选过这门课了")
                            return True
                        else:
                            if attempt < TryTimes:
                                log_callback(f"⚠️ [{course_key}] 第 {attempt} 次失败，正在重试...")
                                time.sleep(BetweenTime)
                            else:
                                log_callback(f"❌ [{course_key}] 所有尝试均失败")
                    except json.JSONDecodeError:
                        log_callback(f"⚠️ [{course_key}] 非法 JSON 响应: {response.text[:200]}")
                else:
                    log_callback(f"❌ [{course_key}] 请求失败，状态码: {response.status_code}")
                    if attempt < TryTimes:
                        time.sleep(BetweenTime)
            except requests.RequestException as e:
                log_callback(f"❌ [{course_key}] 请求异常: {e}")
                if attempt < TryTimes:
                    time.sleep(BetweenTime)
        return False

    def monitor_and_enroll(course_config, course_key):
        """监控并尝试抢指定的一门课"""
        if course_status[course_key]["done"] or stop_flag():
            return
        try:
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
                log_callback(f"❌ [{course_key}] 请求失败: {response.status_code}")
                return
            json_data = response.json()
            if json_data.get("code") != 200:
                log_callback(f"❌ [{course_key}] 接口错误: {json_data.get('msg')}")
                return
            rows = json_data.get("data", {}).get("rows", [])
            if not rows:
                log_callback(f"⚠️ [{course_key}] 未查到课程")
                return
            tc_list = rows[0].get("tcList", [])
            if not tc_list:
                log_callback(f"⚠️ [{course_key}] 无教学班信息")
                return
            teaching_class = tc_list[0]
            selected = teaching_class.get("numberOfSelected")
            capacity = teaching_class.get("classCapacity")
            clazzId = teaching_class.get("JXBID") or teaching_class.get("teachingClassID")
            secretVal = teaching_class.get("secretVal")
            if None in (selected, capacity, clazzId, secretVal):
                log_callback(f"⚠️ [{course_key}] 数据不完整，跳过")
                return
            log_callback(f"📊 [{course_key}] 当前 {selected}/{capacity} 人")
            success = submit_enrollment(clazzId, secretVal, course_config["clazzType"], course_key)
            course_status[course_key]["done"] = True
            if success:
                log_callback(f"🎉 [{course_key}] 抢课完成！")
            else:
                log_callback(f"🚫 [{course_key}] 抢课失败，跳过")
        except Exception as e:
            log_callback(f"❌ [{course_key}] 检查过程异常: {e}")

    # ===== 8. 主循环 =====
    log_callback("🔍 开始准备对多门课程进行自动抢课...")
    while True:
        if stop_flag():
            log_callback("🛑 用户中止，程序退出。")
            break
        all_done = True
        for course_key, status in course_status.items():
            if not status["done"]:
                all_done = False
                monitor_and_enroll(status["config"], course_key)
                if stop_flag():
                    break
        if all_done:
            log_callback("✅ 所有课程抢课流程结束，程序退出。")
            break
        time.sleep(WaitTime)