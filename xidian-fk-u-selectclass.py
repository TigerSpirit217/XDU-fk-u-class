import requests
import json
import time
import urllib.parse

# 注意：这个程序是AI写的！！！
# Powered by Qwen-3

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
    # 需要从cookie中提取Authorization填写在下面
    "Authorization": "*******",
    # 需要填写batch ID（浏览器地址里面有）
    "batchId": "*******",
    "Origin": "https://xk.xidian.edu.cn",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    # 就是浏览器地址
    "Referer": "https://xk.xidian.edu.cn/xsxk/elective/grablessons?batchId=*******",
    # 下面需要填写cookie（按F12刷新界面可以得到）
    "Cookie": "Authorization=*******; route=*******",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0"
}

HEADERS_COURSE = HEADERS_CHECK.copy()
HEADERS_COURSE["Content-Type"] = "application/x-www-form-urlencoded"

# 课程信息在这里（相较于修改teachingClassType和KEY，更建议直接抓包整段复制）
DATA_CHECK = {
    # 这里是课程类别
    "teachingClassType": "****",
    "pageNumber": 1,
    "pageSize": 10,
    "orderBy": "",
    "campus": "S",
    # 这里输入老师的名字，或者课程号码，调用的其实是搜索逻辑
    "KEY": "*******"
}

has_submitted = False  # 防止重复提交

# ================== 抢课请求 ==================
def submit_enrollment(clazzId, secretVal):
    global has_submitted
    if has_submitted:
        return
    has_submitted = True

    # 这里的课程类别也要改，别漏了
    form_data = {
        "clazzType": "TYKC",
        "clazzId": clazzId,
        "secretVal": secretVal
    }
    body = urllib.parse.urlencode(form_data)

    try:
        response = requests.post(COURSE_URL, headers=HEADERS_COURSE, data=body, timeout=10)
        print("🎯 抢课请求已发送！")
        if response.status_code == 200:
            try:
                result = response.json()
                msg = result.get("msg", "未知响应")
                print(f"💡 服务器返回: {msg}")
                if result.get("code") in [200, "200"]:
                    print("✅ 恭喜！抢课成功！")
                elif "已选" in msg or "重复" in msg:
                    print("⚠️ 你可能已经选过这门课了")
                else:
                    print("❌ 抢课失败")
            except json.JSONDecodeError:
                print("⚠️ 非法 JSON 响应:", response.text)
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print("响应内容:", response.text)
    except requests.RequestException as e:
        print(f"❌ 抢课请求异常: {e}")

# ================== 监控与抢课逻辑 ==================
def check_and_enroll():
    global has_submitted
    if has_submitted:
        return

    try:
        response = requests.post(CHECK_URL, headers=HEADERS_CHECK, json=DATA_CHECK, timeout=10)
        if response.status_code == 200:
            try:
                json_data = response.json()
                if json_data.get("code") != 200:
                    print(f"❌ 接口错误: {json_data.get('msg')}")
                    return

                rows = json_data.get("data", {}).get("rows", [])
                if not rows:
                    print("⚠️ 未查到课程")
                    return

                tc_list = rows[0].get("tcList", [])
                if not tc_list:
                    print("⚠️ 无教学班信息")
                    return

                teaching_class = tc_list[0]
                selected = teaching_class.get("numberOfSelected")
                capacity = teaching_class.get("classCapacity")
                clazzId = teaching_class.get("JXBID") or teaching_class.get("teachingClassID")
                secretVal = teaching_class.get("secretVal")

                if None in (selected, capacity, clazzId, secretVal):
                    print("⚠️ 数据不完整，跳过")
                    return

                print(f"📊 当前 {selected}/{capacity} 人")

                # ✅ 核心判断：还有空位？
                if selected < capacity:
                    print(f"🟢 发现空位！尝试抢课 → {clazzId}")
                    submit_enrollment(clazzId, secretVal)
                # else:
                #   print("🚫 已满员，继续监控...")

            except Exception as e:
                print(f"❌ 解析失败: {e}")
        else:
            print(f"❌ 请求失败: {response.status_code}")

    except requests.RequestException as e:
        print(f"❌ 网络异常: {e}")

# ================== 主循环 ==================
if __name__ == "__main__":
    print("🔍 开始监控课程余量，发现空位自动抢课...")
    while True:
        check_and_enroll()
        if has_submitted:
            print("⏸️ 抢课完成，停止监控。")
            break
        time.sleep(3)  # 每3秒检查一次
