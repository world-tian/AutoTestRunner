file_path = '/Users/bytedance/Documents/AutoTestRunner/src/autotest_runner/agent/agent.py'
with open(file_path, 'r') as f:
    content = f.read()

new_block = """            # 寻找生成的 HTML 报告并回传内容
            html_report = None
            import re
            report_match = re.search(r"本地报告已生成:\\s*([^\\n]+)", full_output)
            logger.info(f"REPORT MATCH: {report_match}")
            if report_match:
                latest_report_file = report_match.group(1).strip()
                logger.info(f"REPORT PATH: {latest_report_file}")
                try:
                    with open(latest_report_file, 'r', encoding='utf-8') as f:
                        html_report = f.read()
                    logger.info(f"READ HTML REPORT length: {len(html_report)}")
                    output.append(f"[{finish_time}] 📊 成功读取本地 HTML 报告并准备上报云端: {os.path.basename(latest_report_file)}\\n")
                except Exception as e:
                    logger.error(f"Failed to read html report: {e}")
                    output.append(f"[{finish_time}] ⚠️ 读取本地 HTML 报告失败: {e}\\n")
            else:
                logger.warning("NO MATCH FOUND IN FULL_OUTPUT")
                output.append(f"[{finish_time}] ⚠️ 未能在日志中找到本地 HTML 报告路径\\n")
            
            full_output = "".join(output)"""

old_block = """            # 寻找生成的 HTML 报告并回传内容
            html_report = None
            import re
            report_match = re.search(r"本地报告已生成:\\s*([^\\n]+)", full_output)
            if report_match:
                latest_report_file = report_match.group(1).strip()
                try:
                    with open(latest_report_file, 'r', encoding='utf-8') as f:
                        html_report = f.read()
                    output.append(f"[{finish_time}] 📊 成功读取本地 HTML 报告并准备上报云端: {os.path.basename(latest_report_file)}\\n")
                except Exception as e:
                    logger.error(f"Failed to read html report: {e}")
                    output.append(f"[{finish_time}] ⚠️ 读取本地 HTML 报告失败: {e}\\n")
            else:
                output.append(f"[{finish_time}] ⚠️ 未能在日志中找到本地 HTML 报告路径\\n")
            
            full_output = "".join(output)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, 'w') as f:
        f.write(content)
    print("Patched debug successfully")
else:
    print("Failed to find block")
