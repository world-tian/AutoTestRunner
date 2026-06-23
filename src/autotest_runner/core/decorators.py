def autotest(case_id=None, req_id=None, title=None, priority="P1"):
    """
    用例元数据打标装饰器。
    用于云端同步，不影响本地离线执行。
    """
    def decorator(func):
        func.__autotest_meta__ = {
            "case_id": case_id,
            "req_id": req_id,
            "title": title,
            "priority": priority
        }
        return func
    return decorator
