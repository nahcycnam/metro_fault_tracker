import requests, time, re
from bs4 import BeautifulSoup
import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon
import os
import ctypes


class ReportViewer(QMainWindow):
	def __init__(self, html_content):
		super().__init__()
		self.html_content = html_content
		self.initUI()

	def initUI(self):
		self.setWindowTitle('车站未修复故障报表')
		self.setGeometry(100, 100, 1200, 800)

		# 设置窗口图标（标题栏图标）
		icon_path = self.get_icon_path()
		if os.path.exists(icon_path):
			icon = QIcon(icon_path)
			self.setWindowIcon(icon)
		else:
			print(f"警告: 找不到图标文件 {icon_path}")

		# 创建中央部件
		central_widget = QWidget()
		self.setCentralWidget(central_widget)

		# 创建布局
		layout = QVBoxLayout(central_widget)

		# 创建Web视图
		self.web_view = QWebEngineView()
		layout.addWidget(self.web_view)

		# 加载HTML内容
		self.web_view.setHtml(self.html_content)

		# 设置窗口标志，使其可以最大化
		self.setWindowFlags(Qt.WindowType.WindowMaximizeButtonHint |
							Qt.WindowType.WindowMinimizeButtonHint |
							Qt.WindowType.WindowCloseButtonHint)

	def get_icon_path(self):
		"""获取图标文件路径"""
		# 首先尝试当前脚本目录
		current_dir = os.path.dirname(os.path.abspath(__file__))
		icon_path = os.path.join(current_dir, 'logo.ico')

		# 如果不存在，尝试exe所在目录（打包后）
		if not os.path.exists(icon_path) and hasattr(sys, 'frozen'):
			icon_path = os.path.join(os.path.dirname(sys.executable), 'logo.ico')

		return icon_path


def set_taskbar_icon(app):
	"""设置Windows任务栏图标"""
	try:
		# 获取图标文件路径
		current_dir = os.path.dirname(os.path.abspath(__file__))
		icon_path = os.path.join(current_dir, 'logo.ico')

		if not os.path.exists(icon_path) and hasattr(sys, 'frozen'):
			icon_path = os.path.join(os.path.dirname(sys.executable), 'logo.ico')

		if os.path.exists(icon_path):
			# 方法1: 设置应用程序图标
			app.setWindowIcon(QIcon(icon_path))

			# 方法2: 使用Windows API设置任务栏图标
			# 这需要Windows和ctypes
			try:
				# 获取应用程序句柄
				app_id = u"gzmetro.faultreport.viewer.1.0"  # 自定义AppUserModelID
				ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
			except AttributeError:
				# 如果不是Windows系统，忽略
				pass

			print(f"已设置任务栏图标: {icon_path}")
		else:
			print(f"警告: 找不到图标文件 {icon_path}")
	except Exception as e:
		print(f"设置任务栏图标时出错: {e}")


def get_lims_report(station='0508'):
	# 获取sessionId
	timestamp = round(time.time() * 1000)
	url = f'http://frpt.gzmetro.com/webroot/decision/view/report?viewlet=02_LMIS/车站管理/车站未修复故障.cpt&_={timestamp}&CUST_LINENUM=L{station[:2]}&CUST_STATION=L{station[:2]}Z{station[-2:]}'

	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.246 Safari/537.36 Qaxbrowser",
	}
	s = requests.Session()
	r = s.get(url, headers=headers)
	session_id = re.search(r'sessionID=([a-f0-9\-]+)', r.text).group(1)

	# LMIS报表
	timestamp = round(time.time() * 1000)
	url = f'http://frpt.gzmetro.com/webroot/decision/view/report?_={timestamp}&__boxModel__=true&op=page_content&pn=1&__webpage__=true&_paperWidth=423&_paperHeight=883&__fit__=false'
	headers["sessionID"] = session_id
	r = s.get(url, headers=headers)
	soup = BeautifulSoup(r.json()['html'], 'lxml')
	tbody = soup.body.div.div.div.div.table.tbody
	trs = tbody.find_all('tr')
	for div in trs[6].find_all('div'):
		if div.string != '1' and div.string:
			return str(soup)
	else:
		return


def remove_scroll_properties(html_content):
	soup = BeautifulSoup(html_content, 'lxml')

	# 定位三个目标元素
	targets = {
		'frozen-north': 'scroll',
		'frozen-west': 'scroll',
		'frozen-center': 'scroll'
	}

	for div_id, scroll_value in targets.items():
		div = soup.find('div', id=div_id)
		if div and div.has_attr('style'):
			# 替换overflow属性中的scroll值
			current_style = div['style']
			new_style = current_style.replace(scroll_value, 'llorcs')
			div['style'] = new_style

	return str(soup)


def background_color_rgb(html_content):
	soup = BeautifulSoup(html_content, 'lxml')

	tbody = soup.body.div.div.div.div.table.tbody
	trs = tbody.find_all('tr')

	for i in range(7, len(trs[4].find_all('div')[2:]), 11):
		div = trs[4].find_all('div')[2:][i - 4]
		if div.string and div.string.strip() == "等待批准":
			td = div.parent if div.parent.name == 'td' else None
			if td:
				td['style'] = "background-color:rgb(255,0,0);"

		fault_date = trs[4].find_all('div')[2:][i - 1].string
		report_date = trs[4].find_all('div')[2:][i].string
		# 定义时间格式
		time_format = "%Y-%m-%d %H:%M:%S"

		# 转换为datetime对象
		dt_fault = datetime.strptime(fault_date, time_format)
		dt_report = datetime.strptime(report_date, time_format)

		# 比较时间
		if dt_fault >= dt_report:
			for j in range(i - 1, i + 1):
				div = trs[4].find_all('div')[2:][j]
				td = div.parent if div.parent.name == 'td' else None
				if td:
					td['style'] = "background-color:rgb(255,0,0);"

		# 计算时间差
		delta = dt_report - dt_fault

		# 返回是否超过24小时
		if delta > timedelta(hours=24):
			for j in range(i - 1, i + 1):
				div = trs[4].find_all('div')[2:][j]
				td = div.parent if div.parent.name == 'td' else None
				if td:
					td['style'] = "background-color:rgb(255,0,0);"

	return str(soup)


def inject_css_to_html(html):
	"""直接向HTML中注入CSS样式，而不保存到文件"""
	soup = BeautifulSoup(html, 'lxml')
	head = soup.find('head')
	if not head:
		head = soup.new_tag('head')
		soup.html.insert(0, head)

	# 读取CSS文件内容并直接添加到style标签中
	css_content = ""
	css_files = [
		'css/finereport.css',
		'css/toolbar.css'
	]

	style_tag = soup.new_tag('style')
	for css_file in css_files:
		try:
			with open(css_file, 'r', encoding='utf-8') as f:
				css_content += f.read() + "\n"
		except FileNotFoundError:
			print(f"警告: 找不到CSS文件 {css_file}")

	if css_content:
		style_tag.string = css_content
		head.append(style_tag)

	return str(soup)


def main():
	# 在创建QApplication之前设置AppUserModelID（Windows任务栏图标的关键）
	try:
		# 设置唯一的AppUserModelID
		app_id = u"gzmetro.faultreport.viewer.1.0"
		ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
		print(f"已设置AppUserModelID: {app_id}")
	except AttributeError:
		print("非Windows系统，跳过AppUserModelID设置")
	except Exception as e:
		print(f"设置AppUserModelID时出错: {e}")

	# 创建应用程序
	app = QApplication(sys.argv)

	# 设置应用程序图标（任务栏图标）
	icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.ico')
	if not os.path.exists(icon_path) and hasattr(sys, 'frozen'):
		icon_path = os.path.join(os.path.dirname(sys.executable), 'logo.ico')

	if os.path.exists(icon_path):
		app.setWindowIcon(QIcon(icon_path))
		print(f"已设置应用程序图标: {icon_path}")
	else:
		print(f"警告: 找不到图标文件 {icon_path}")

	# 获取报表内容
	html = get_lims_report()

	if html:
		# 处理HTML
		html = remove_scroll_properties(html)
		html = background_color_rgb(html)
		html = inject_css_to_html(html)

		# 创建并显示窗口
		viewer = ReportViewer(html)
		viewer.show()

		sys.exit(app.exec())
	else:
		print("没有获取到报表数据")
		# 可以在这里添加错误处理，比如打开原始网页
		import webbrowser
		webbrowser.open(
			"http://frpt.gzmetro.com/webroot/decision/view/report?viewlet=02_LMIS/车站管理/车站未修复故障.cpt&_=1748890686151&CUST_LINENUM=L05&CUST_STATION=L05Z08")


if __name__ == '__main__':
	main()
