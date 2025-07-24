"""
智能记忆功能自动化测试
使用Playwright模拟用户对话并验证记忆功能
"""

import asyncio
import time
import json
from playwright.async_api import async_playwright
from memory_test_cases import MemoryTestCases

class IntelligentMemoryTester:
    """智能记忆功能自动化测试器"""
    
    def __init__(self, base_url="http://localhost:8503"):
        self.base_url = base_url
        self.browser = None
        self.page = None
        self.test_results = []
        
    async def setup(self):
        """设置测试环境"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)  # 设置为False以便观察测试过程
        self.page = await self.browser.new_page()
        
        # 导航到应用
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state('networkidle')
        
        # 登录（如果需要）
        await self.login_if_needed()
        
        # 导航到智能对话页面
        await self.navigate_to_chat()
        
    async def login_if_needed(self):
        """如果需要登录则进行登录"""
        try:
            # 检查是否在登录页面
            login_button = await self.page.query_selector('button:has-text("登录")')
            if login_button:
                print("🔐 检测到登录页面，正在登录...")
                
                # 填写用户名和密码
                await self.page.fill('input[placeholder*="用户名"], input[type="text"]', 'admin')
                await self.page.fill('input[placeholder*="密码"], input[type="password"]', 'admin123')
                
                # 点击登录按钮
                await login_button.click()
                
                # 等待登录完成
                await self.page.wait_for_load_state('networkidle')
                print("✅ 登录成功")
                
        except Exception as e:
            print(f"⚠️ 登录过程中出现问题: {e}")
    
    async def navigate_to_chat(self):
        """导航到智能对话页面"""
        try:
            # 查找智能对话标签
            chat_tab = await self.page.query_selector('div[role="tab"]:has-text("智能对话")')
            if chat_tab:
                await chat_tab.click()
                await self.page.wait_for_timeout(1000)
                print("📱 已切换到智能对话页面")
            else:
                print("⚠️ 未找到智能对话标签，可能已经在正确页面")
                
        except Exception as e:
            print(f"⚠️ 导航到对话页面时出错: {e}")
    
    async def send_message(self, message: str, wait_for_response: bool = True):
        """发送消息到聊天界面"""
        try:
            # 查找输入框
            input_selectors = [
                'textarea[placeholder*="输入"]',
                'input[placeholder*="输入"]',
                'textarea',
                'input[type="text"]'
            ]
            
            input_element = None
            for selector in input_selectors:
                input_element = await self.page.query_selector(selector)
                if input_element:
                    break
            
            if not input_element:
                raise Exception("未找到消息输入框")
            
            # 清空输入框并输入消息
            await input_element.clear()
            await input_element.fill(message)
            
            # 发送消息（按Enter或点击发送按钮）
            await input_element.press('Enter')
            
            print(f"📤 已发送消息: {message}")
            
            if wait_for_response:
                # 等待AI回复
                await self.wait_for_ai_response()
                
        except Exception as e:
            print(f"❌ 发送消息失败: {e}")
            raise
    
    async def wait_for_ai_response(self, timeout: int = 30):
        """等待AI回复"""
        try:
            # 等待加载指示器消失或AI回复出现
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # 检查是否有"Running..."或加载指示器
                running_indicator = await self.page.query_selector('img[alt="Running..."]')
                if not running_indicator:
                    # 等待一下确保回复完全加载
                    await self.page.wait_for_timeout(2000)
                    break
                    
                await self.page.wait_for_timeout(1000)
            
            print("✅ AI回复完成")
            
        except Exception as e:
            print(f"⚠️ 等待AI回复时出错: {e}")
    
    async def get_chat_history(self):
        """获取聊天历史"""
        try:
            # 这里需要根据实际的聊天界面结构来获取聊天历史
            # 由于使用了iframe，可能需要特殊处理
            
            # 尝试获取聊天消息
            messages = await self.page.query_selector_all('.message, .chat-message, [data-testid*="message"]')
            
            chat_history = []
            for message in messages:
                text = await message.inner_text()
                chat_history.append(text)
            
            return chat_history
            
        except Exception as e:
            print(f"⚠️ 获取聊天历史失败: {e}")
            return []
    
    async def check_memory_indicators(self):
        """检查记忆功能指示器"""
        try:
            indicators = {}
            
            # 检查记忆学习状态
            learning_status = await self.page.query_selector('text="AI正在积极学习中"')
            indicators['learning_active'] = learning_status is not None
            
            # 检查记忆统计
            memory_count = await self.page.query_selector('[data-testid*="memory-count"], text*="总记忆数量"')
            if memory_count:
                count_text = await memory_count.inner_text()
                indicators['memory_count'] = count_text
            
            # 检查是否显示了使用的记忆
            memory_expander = await self.page.query_selector('text*="本次对话使用了"')
            indicators['memory_used'] = memory_expander is not None
            
            return indicators
            
        except Exception as e:
            print(f"⚠️ 检查记忆指示器失败: {e}")
            return {}
    
    async def run_test_case(self, test_case: dict):
        """运行单个测试用例"""
        print(f"\n🧪 开始测试: {test_case['name']}")
        
        test_result = {
            'name': test_case['name'],
            'status': 'running',
            'details': [],
            'errors': []
        }
        
        try:
            # 如果有设置记忆，先设置
            if 'setup_memories' in test_case:
                for memory in test_case['setup_memories']:
                    await self.send_message(f"请记住：{memory}")
                    await self.page.wait_for_timeout(2000)
            
            # 执行对话
            for i, conversation in enumerate(test_case['conversation']):
                user_message = conversation['user']
                
                print(f"  💬 对话 {i+1}: {user_message}")
                
                # 发送消息
                await self.send_message(user_message)
                
                # 检查记忆指示器
                memory_indicators = await self.check_memory_indicators()
                
                # 验证预期结果
                step_result = {
                    'message': user_message,
                    'memory_indicators': memory_indicators,
                    'expected': conversation,
                    'passed': True
                }
                
                # 检查是否符合预期
                if 'expected_memory_retrieval' in conversation:
                    expected = conversation['expected_memory_retrieval']
                    actual = memory_indicators.get('memory_used', False)
                    if expected != actual:
                        step_result['passed'] = False
                        step_result['error'] = f"记忆检索预期: {expected}, 实际: {actual}"
                
                test_result['details'].append(step_result)
                
                # 等待一下再进行下一步
                await self.page.wait_for_timeout(3000)
            
            # 计算测试结果
            passed_steps = sum(1 for detail in test_result['details'] if detail['passed'])
            total_steps = len(test_result['details'])
            
            if passed_steps == total_steps:
                test_result['status'] = 'passed'
                print(f"  ✅ 测试通过 ({passed_steps}/{total_steps})")
            else:
                test_result['status'] = 'failed'
                print(f"  ❌ 测试失败 ({passed_steps}/{total_steps})")
            
        except Exception as e:
            test_result['status'] = 'error'
            test_result['errors'].append(str(e))
            print(f"  💥 测试出错: {e}")
        
        self.test_results.append(test_result)
        return test_result
    
    async def run_all_tests(self):
        """运行所有测试用例"""
        print("🚀 开始智能记忆功能自动化测试")
        
        # 获取所有测试用例
        all_test_cases = MemoryTestCases.get_all_test_cases()
        
        # 运行每个类别的测试
        for category, test_cases in all_test_cases.items():
            print(f"\n📂 测试类别: {category}")
            
            for test_case in test_cases:
                await self.run_test_case(test_case)
                
                # 清空聊天历史，为下一个测试做准备
                await self.clear_chat_if_possible()
        
        # 生成测试报告
        self.generate_test_report()
    
    async def clear_chat_if_possible(self):
        """尝试清空聊天历史"""
        try:
            clear_button = await self.page.query_selector('button:has-text("清空"), button:has-text("清除")')
            if clear_button:
                await clear_button.click()
                await self.page.wait_for_timeout(1000)
                print("  🧹 已清空聊天历史")
        except Exception as e:
            print(f"  ⚠️ 清空聊天失败: {e}")
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n📊 测试报告")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['status'] == 'passed')
        failed_tests = sum(1 for result in self.test_results if result['status'] == 'failed')
        error_tests = sum(1 for result in self.test_results if result['status'] == 'error')
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"错误: {error_tests} 💥")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        # 详细结果
        print("\n📋 详细结果:")
        for result in self.test_results:
            status_icon = {"passed": "✅", "failed": "❌", "error": "💥"}[result['status']]
            print(f"  {status_icon} {result['name']}")
            
            if result['errors']:
                for error in result['errors']:
                    print(f"    💥 {error}")
        
        # 保存报告到文件
        with open('memory_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: memory_test_report.json")
    
    async def cleanup(self):
        """清理测试环境"""
        if self.browser:
            await self.browser.close()

async def main():
    """主测试函数"""
    tester = IntelligentMemoryTester()
    
    try:
        await tester.setup()
        await tester.run_all_tests()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
