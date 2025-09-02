import requests
from bs4 import BeautifulSoup
import re
import time

# 注意：这个程序是AI写的！！！
# Powered by Deepseek-V3

# 你需要修改第52行、第183-184行、第189-196行

class PhysicsExperimentSystem:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://wlsy.xidian.edu.cn/PhyEws"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def login(self, username, password):
        """登录系统"""
        # 首先获取登录页面
        login_url = f"{self.base_url}/default.aspx"
        response = self.session.get(login_url, headers=self.headers)

        # 解析隐藏字段
        soup = BeautifulSoup(response.text, 'html.parser')
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

        # 准备登录数据
        login_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_generator,
            '__EVENTVALIDATION': event_validation,
            'login1$StuLoginID': username,
            'login1$StuPassword': password,
            'login1$UserRole': 'Student',
            'login1$btnLogin.x': '26',
            'login1$btnLogin.y': '9'
        }

        # 发送登录请求
        response = self.session.post(login_url, data=login_data, headers=self.headers)
        return '你的姓名' in response.text  # 检查是否登录成功

    def get_dropdown_options(self):
        """获取四个下拉框的选项"""
        # 访问选课页面
        select_url = f"{self.base_url}/student/addexpe.aspx"
        response = self.session.get(select_url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 获取四个下拉框
        week_list = soup.find('select', {'name': 'ExpeWeekList'})
        time_list = soup.find('select', {'name': 'ExpeTimeList'})
        class_list = soup.find('select', {'name': 'ExpeClassList'})
        name_list = soup.find('select', {'name': 'ExpeNameList'})

        # 提取选项
        week_options = self.extract_options(week_list)
        time_options = self.extract_options(time_list)
        class_options = self.extract_options(class_list)
        name_options = self.extract_options(name_list)

        return week_options, time_options, class_options, name_options

    def extract_options(self, select_element):
        """从select元素中提取选项"""
        if not select_element:
            return []

        options = []
        for option in select_element.find_all('option'):
            options.append({
                'value': option.get('value', ''),
                'text': option.text.strip()
            })
        return options

    def print_options(self, week_options, time_options, class_options, name_options):
        """打印选项"""
        print("=" * 50)
        print("周次选项 (ExpeWeekList):")
        for option in week_options:
            print(f"  值: {option['value']}, 文本: {option['text']}")

        print("\n时间选项 (ExpeTimeList):")
        for option in time_options:
            print(f"  值: {option['value']}, 文本: {option['text']}")

        print("\n类别选项 (ExpeClassList):")
        for option in class_options:
            print(f"  值: {option['value']}, 文本: {option['text']}")

        print("\n课程选项 (ExpeNameList):")
        for option in name_options:
            print(f"  值: {option['value']}, 文本: {option['text']}")
        print("=" * 50)

    def select_experiment(self, week, time_slot, class_id, experiment_id):
        """选择实验课程并返回服务器原始响应"""
        # 更新请求头以匹配选课请求
        select_headers = self.headers.copy()
        select_headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'http://wlsy.xidian.edu.cn',
            'Sec-GPC': '1',
            'Referer': 'http://wlsy.xidian.edu.cn/PhyEws/student/addexpe.aspx',
        })

        # 首先获取页面以获取必要的隐藏字段
        select_url = f"{self.base_url}/student/addexpe.aspx"
        response = self.session.get(select_url, headers=select_headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 获取必要的隐藏字段
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        last_focus = soup.find('input', {'name': '__LASTFOCUS'})['value'] if soup.find('input',
                                                                                       {'name': '__LASTFOCUS'}) else ''

        # 准备选课数据
        select_data = {
            '__EVENTTARGET': 'ExpeClassList',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': last_focus,
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_generator,
            '__EVENTVALIDATION': event_validation,
            'ExpeWeekList': week,
            'ExpeTimeList': time_slot,
            'ExpeClassList': class_id,
            'ExpeNameList': experiment_id,
            'btnAdd.x': '35',
            'btnAdd.y': '14',
            't1': ''
        }

        # 发送选课请求
        response = self.session.post(select_url, data=select_data, headers=select_headers)

        # 直接返回服务器响应文本
        return response.text

    def check_selection_success(self, response_text):
        """检查选课是否成功"""
        soup = BeautifulSoup(response_text, 'html.parser')

        # 检查是否有错误信息
        error_msg = soup.find('span', {'id': re.compile(r'.*ValidationSummary.*')})
        if error_msg and error_msg.text.strip():
            return False, f"选课失败: {error_msg.text.strip()}"

        # 检查是否成功添加到已选实验列表
        orders_table = soup.find('span', {'id': 'Orders'})
        if orders_table:
            rows = orders_table.find_all('tr')
            if len(rows) > 1:  # 有数据行表示选课成功
                return True, "选课成功!"

        # 检查是否有其他成功提示
        success_msg = soup.find(text=re.compile(r'.*选课成功.*|.*已成功选择.*'))
        if success_msg:
            return True, "选课成功!"

        return False, "选课结果未知，请检查页面内容"


def main():
    # 创建系统实例
    system = PhysicsExperimentSystem()

    # 登录信息
    username = "你的账号"
    password = "你的密码"

    # 定义8门课程的四要素
    courses = [
        # 格式: (周次, 时间, 类别, 课程, 课程名称)
        ("2", "1C", "7001", "B04", "冲击法测量直螺线管磁场实验"),
        ("3", "1C", "7001", "B07", "霍尔效应测量磁场实验"),
        ("4", "1C", "7001", "B06", "低电阻的测量实验"),
        ("5", "1C", "7001", "B14", "劈尖干涉实验"),
        ("6", "4C", "7001", "B10", "单缝衍射光强分布实验"),
        ("7", "1C", "7001", "B17", "复摆实验"),
        ("8", "1C", "7001", "B18", "拉伸法测量杨氏弹性模量实验"),
        ("9", "1B", "7001", "B19", "扭摆法测量切变模量实验"),
    ]

    # 登录系统
    if system.login(username, password):
        print("登录成功!")

        # 获取下拉框选项
        week_options, time_options, class_options, name_options = system.get_dropdown_options()

        # 打印选项
        system.print_options(week_options, time_options, class_options, name_options)

        # 初始化结果统计
        results = []

        # 顺序发送8门课程的选课请求
        for i, (week, time_slot, class_id, experiment_id, course_name) in enumerate(courses, 1):
            print(f"\n正在尝试选课 {i}/8: {course_name}")
            print(f"参数: 周次={week}, 时间={time_slot}, 类别={class_id}, 课程={experiment_id}")

            # 每门课程最多尝试3次
            success = False
            attempts = 0
            max_attempts = 3

            while not success and attempts < max_attempts:
                attempts += 1
                print(f"  尝试 {attempts}/{max_attempts}...")

                # 执行选课
                response_text = system.select_experiment(week, time_slot, class_id, experiment_id)

                # 检查选课结果
                success, message = system.check_selection_success(response_text)

                if success:
                    print(f"  ✓ {message}")
                else:
                    print(f"  ✗ {message}")

                    # 如果不是最后一次尝试，等待一段时间再重试
                    if attempts < max_attempts:
                        print("  等待0.2秒后重试...")
                        time.sleep(0.2)

            # 记录结果
            results.append({
                'course': course_name,
                'week': week,
                'time': time_slot,
                'class': class_id,
                'experiment': experiment_id,
                'success': success,
                'attempts': attempts,
                'message': message
            })

            # 如果选课成功，等待一段时间再尝试下一门课程
            if success:
                print("  等待0.2秒后继续下一门课程...")
                time.sleep(0.2)

        # 打印最终结果统计
        print("\n" + "=" * 80)
        print("选课结果统计:")
        print("=" * 80)

        success_count = 0
        for result in results:
            status = "成功" if result['success'] else "失败"
            print(f"{result['course']}: {status} (尝试次数: {result['attempts']})")
            if not result['success']:
                print(f"  失败原因: {result['message']}")

            if result['success']:
                success_count += 1

        print(f"\n总计: 成功 {success_count}/8, 失败 {8 - success_count}")
        print("=" * 80)

    else:
        print("登录失败，请检查用户名和密码")


if __name__ == "__main__":
    main()