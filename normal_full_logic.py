# normal_full_logic.py
import requests
import json
import time
import re
import urllib.parse
from typing import Dict, Any, Callable


def run_normal_full(config: Dict[str, Any], log_callback: Callable[[str], None], stop_flag: Callable[[], bool]):
    """
    执行普通/体育课程补选监控（无限轮询，发现空位即抢，仅抢一次）

    :param config: 配置字典，包含以下字段：
        - UserAgent (str)
        - AcceptLanguage (str)
        - BatchID (str)
        - Cookie (str)
        - campus (str, 默认 "S")
        - teachingClassType (str)
        - KEY (str)
        - ClazzType (str)

        【以下为原脚本有但 GUI 未直接对应，此处设默认值】
        - WaitTime (int, 轮询间隔秒数，默认 5)

    :param log_callback: 日志输出回调函数，如 log(msg)
    :param stop_flag: 停止标志回调，返回 True 表示应停止
    """

    # ===== 1. 从 config 提取参数 =====
    UserAgentTypeIn = config.get("UserAgent", "").strip()
    AcceptLanguage = config.get("AcceptLanguage", "").strip()
    BatchID = config.get("BatchID", "").strip()
    CookieIsHere = config.get("Cookie", "").strip()
    campus = config.get("campus", "S")
    teachingClassType = config.get("teachingClassType", "TJKC")
    KEY = config.get("KEY", "").strip()
    ClazzType = config.get("ClazzType", teachingClassType)

    # WaitTime 在原脚本中是轮询间隔，GUI 中对应的是 BetweenTime 或类似字段
    # 但在补选 Tab 中，GUI 实际传入的是 "BetweenTime"，这里兼容处理
    WaitTime = config.get("WaitTime", config.get("BetweenTime", 5))

    # ===== 2. 验证 Cookie =====
    match = re.search(r'Authorization=([^;]+)', CookieIsHere)
    if not match:
        log_callback("❌ 你的 cookie 有问题，请检查是否包含 Authorization 字段。")
        return
    Author = match.group(1)

    # ===== 3. 构造请求头和 URL =====
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

    # ===== 4. 全局状态（防止重复提交）=====
    has_submitted = False

    # ===== 5. 抢课请求函数 =====
    def submit_enrollment(clazzId, secretVal):
        nonlocal has_submitted
        if has_submitted or stop_flag():
            return
        has_submitted = True
        form_data = {
            "clazzType": ClazzType,
            "clazzId": clazzId,
            "secretVal": secretVal
        }
        body = urllib.parse.urlencode(form_data)
        try:
            log_callback("🎯 抢课请求已发送！")
            response = requests.post(COURSE_URL, headers=HEADERS_COURSE, data=body, timeout=10)
            if response.status_code == 200:
                try:
                    result = response.json()
                    msg = result.get("msg", "未知响应")
                    log_callback(f"💡 服务器返回: {msg}")
                    if result.get("code") in [200, "200"]:
                        log_callback("✅ 恭喜！抢课成功！")
                    elif "已选" in msg or "重复" in msg:
                        log_callback("⚠️ 你可能已经选过这门课了")
                    else:
                        log_callback("❌ 抢课失败")
                except json.JSONDecodeError:
                    log_callback(f"⚠️ 非法 JSON 响应: {response.text[:200]}")
            else:
                log_callback(f"❌ 请求失败，状态码: {response.status_code}")
                log_callback(f"响应内容: {response.text[:200]}")
        except requests.RequestException as e:
            log_callback(f"❌ 抢课请求异常: {e}")

    # ===== 6. 监控与抢课逻辑 =====
    def check_and_enroll():
        nonlocal has_submitted
        if has_submitted or stop_flag():
            return
        try:
            DATA_CHECK = {
                "teachingClassType": teachingClassType,
                "pageNumber": 1,
                "pageSize": 10,
                "orderBy": "",
                "campus": campus,
                "KEY": KEY
            }
            response = requests.post(CHECK_URL, headers=HEADERS_CHECK, json=DATA_CHECK, timeout=10)
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    if json_data.get("code") != 200:
                        log_callback(f"❌ 接口错误: {json_data.get('msg')}")
                        return
                    rows = json_data.get("data", {}).get("rows", [])
                    if not rows:
                        log_callback("⚠️ 未查到课程")
                        return
                    tc_list = rows[0].get("tcList", [])
                    if not tc_list:
                        log_callback("⚠️ 无教学班信息")
                        return
                    teaching_class = tc_list[0]
                    selected = teaching_class.get("numberOfSelected")
                    capacity = teaching_class.get("classCapacity")
                    clazzId = teaching_class.get("JXBID") or teaching_class.get("teachingClassID")
                    secretVal = teaching_class.get("secretVal")
                    if None in (selected, capacity, clazzId, secretVal):
                        log_callback("⚠️ 数据不完整，跳过")
                        return
                    log_callback(f"📊 当前 {selected}/{capacity} 人")
                    if selected < capacity:
                        log_callback(f"🟢 发现空位！尝试抢课 → {clazzId}")
                        submit_enrollment(clazzId, secretVal)
                except Exception as e:
                    log_callback(f"❌ 解析失败: {e}")
            else:
                log_callback(f"❌ 请求失败: {response.status_code}")
        except requests.RequestException as e:
            log_callback(f"❌ 网络异常: {e}")

    # ===== 7. 主循环 =====
    log_callback("🔍 开始监控课程余量，发现空位自动抢课...")
    while True:
        if stop_flag():
            log_callback("🛑 用户中止，监控已停止。")
            break
        check_and_enroll()
        if has_submitted:
            log_callback("⏸️ 抢课完成，停止监控。")
            break
        time.sleep(WaitTime)